"""
build_database.py — ETL Data Pipeline (Phase 3)
================================================
Builds meaning.data and index.data from scratch.

Workflow:
    1. EXTRACT  — Loads the SAMPLE_DATA dictionary (embedded, 100 words)
                  and optionally merges external CSV/JSON files if present.
    2. TRANSFORM — Sorts by keyword alphabetically to enable binary search.
    3. LOAD      — Writes binary meaning.data + 53-byte fixed-width index.data.

Run:
    python build_database.py

To extend with real data:
    Place a CSV at data/raw/en_vi.csv  (columns: word, meaning)
    Place JSON  at data/raw/ipa.json   (format: {"word": "/ɪpɑː/", ...})
    Run again — the pipeline merges everything automatically.
"""

import csv
import json
import os
import sys

# Fix Windows terminal Unicode (cp1252 → UTF-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace') # type: ignore

# ── Constants matching IndexNavigator ──────────────────────────────────────
RECORD_SIZE = 53
KEY_WIDTH   = 32
OFF_WIDTH   = 12
LEN_WIDTH   = 8

DATA_DIR    = os.path.join(os.path.dirname(__file__), "data")
MEANING_FILE = os.path.join(DATA_DIR, "meaning.data")
INDEX_FILE   = os.path.join(DATA_DIR, "index.data")
RAW_DIR      = os.path.join(DATA_DIR, "raw")

# ── Embedded Sample Data ────────────────────────────────────────────────────
# 100 common English words with Vietnamese meanings, IPA, word class & examples
SAMPLE_DATA = [
    {"word": "hello", "meanings": ["xin chào", "chào hỏi"], "phonetic": "/həˈləʊ/", "word_class": "interjection",
     "examples": [["Hello! How are you?", "Xin chào! Bạn khỏe không?"]]},
    {"word": "abandon", "meanings": ["từ bỏ", "bỏ rơi"], "phonetic": "/əˈbæn.dən/", "word_class": "verb",
     "examples": [["He abandoned his car on the motorway.", "Anh ấy bỏ xe trên đường cao tốc."]]},
    {"word": "ability", "meanings": ["khả năng", "năng lực"], "phonetic": "/əˈbɪl.ɪ.ti/", "word_class": "noun",
     "examples": [["She has the ability to learn quickly.", "Cô ấy có khả năng học nhanh."]]},
    {"word": "absence", "meanings": ["sự vắng mặt", "sự thiếu vắng"], "phonetic": "/ˈæb.səns/", "word_class": "noun",
     "examples": [["His absence was noticed by everyone.", "Sự vắng mặt của anh ấy được mọi người chú ý."]]},
    {"word": "absolute", "meanings": ["tuyệt đối", "hoàn toàn"], "phonetic": "/ˈæb.sə.luːt/", "word_class": "adjective",
     "examples": [["This is an absolute truth.", "Đây là sự thật tuyệt đối."]]},
    {"word": "accept", "meanings": ["chấp nhận", "tiếp nhận"], "phonetic": "/əkˈsept/", "word_class": "verb",
     "examples": [["Please accept my apology.", "Xin hãy chấp nhận lời xin lỗi của tôi."]]},
    {"word": "achieve", "meanings": ["đạt được", "hoàn thành"], "phonetic": "/əˈtʃiːv/", "word_class": "verb",
     "examples": [["He achieved his goal.", "Anh ấy đạt được mục tiêu của mình."]]},
    {"word": "adapt", "meanings": ["thích nghi", "điều chỉnh"], "phonetic": "/əˈdæpt/", "word_class": "verb",
     "examples": [["Animals adapt to their environment.", "Động vật thích nghi với môi trường của chúng."]]},
    {"word": "admire", "meanings": ["ngưỡng mộ", "khâm phục"], "phonetic": "/ədˈmaɪər/", "word_class": "verb",
     "examples": [["I admire her courage.", "Tôi ngưỡng mộ lòng dũng cảm của cô ấy."]]},
    {"word": "adventure", "meanings": ["cuộc phiêu lưu", "mạo hiểm"], "phonetic": "/ədˈven.tʃər/", "word_class": "noun",
     "examples": [["Life is a great adventure.", "Cuộc sống là một cuộc phiêu lưu vĩ đại."]]},
    {"word": "alliance", "meanings": ["liên minh", "đồng minh"], "phonetic": "/əˈlaɪ.əns/", "word_class": "noun",
     "examples": [["The two countries formed an alliance.", "Hai quốc gia thành lập liên minh."]]},
    {"word": "ambition", "meanings": ["tham vọng", "hoài bão"], "phonetic": "/æmˈbɪʃ.ən/", "word_class": "noun",
     "examples": [["Her ambition drove her to succeed.", "Tham vọng thúc đẩy cô ấy đi đến thành công."]]},
    {"word": "ancient", "meanings": ["cổ xưa", "thời cổ đại"], "phonetic": "/ˈeɪn.ʃənt/", "word_class": "adjective",
     "examples": [["This is an ancient temple.", "Đây là một ngôi đền cổ xưa."]]},
    {"word": "anxiety", "meanings": ["lo âu", "sự lo lắng"], "phonetic": "/æŋˈzaɪ.ɪ.ti/", "word_class": "noun",
     "examples": [["Anxiety can be treated with therapy.", "Lo âu có thể được điều trị bằng liệu pháp."]]},
    {"word": "apple", "meanings": ["quả táo", "cây táo"], "phonetic": "/ˈæp.əl/", "word_class": "noun",
     "examples": [["An apple a day keeps the doctor away.", "Một quả táo mỗi ngày giúp bạn không cần gặp bác sĩ."]]},
    {"word": "approach", "meanings": ["tiếp cận", "phương pháp tiếp cận"], "phonetic": "/əˈprəʊtʃ/", "word_class": "verb",
     "examples": [["We need a new approach to solve this.", "Chúng ta cần một cách tiếp cận mới để giải quyết điều này."]]},
    {"word": "arrange", "meanings": ["sắp xếp", "bố trí"], "phonetic": "/əˈreɪndʒ/", "word_class": "verb",
     "examples": [["She arranged the flowers beautifully.", "Cô ấy cắm hoa rất đẹp."]]},
    {"word": "atmosphere", "meanings": ["bầu không khí", "khí quyển"], "phonetic": "/ˈæt.mə.sfɪər/", "word_class": "noun",
     "examples": [["The atmosphere in the room was tense.", "Bầu không khí trong phòng rất căng thẳng."]]},
    {"word": "authority", "meanings": ["quyền lực", "thẩm quyền"], "phonetic": "/ɔːˈθɒr.ɪ.ti/", "word_class": "noun",
     "examples": [["The police have the authority to arrest.", "Cảnh sát có thẩm quyền bắt giữ."]]},
    {"word": "balance", "meanings": ["sự cân bằng", "thăng bằng"], "phonetic": "/ˈbæl.əns/", "word_class": "noun",
     "examples": [["Work-life balance is important.", "Cân bằng công việc và cuộc sống rất quan trọng."]]},
    {"word": "barrier", "meanings": ["rào cản", "chướng ngại vật"], "phonetic": "/ˈbær.i.ər/", "word_class": "noun",
     "examples": [["Language can be a barrier.", "Ngôn ngữ có thể là một rào cản."]]},
    {"word": "benefit", "meanings": ["lợi ích", "lợi thế"], "phonetic": "/ˈben.ɪ.fɪt/", "word_class": "noun",
     "examples": [["Exercise has many health benefits.", "Tập thể dục có nhiều lợi ích sức khỏe."]]},
    {"word": "brilliant", "meanings": ["xuất sắc", "tài ba", "rực rỡ"], "phonetic": "/ˈbrɪl.i.ənt/", "word_class": "adjective",
     "examples": [["She has a brilliant mind.", "Cô ấy có một trí tuệ xuất sắc."]]},
    {"word": "capable", "meanings": ["có khả năng", "có năng lực"], "phonetic": "/ˈkeɪ.pə.bəl/", "word_class": "adjective",
     "examples": [["He is capable of doing the job.", "Anh ấy có khả năng làm công việc này."]]},
    {"word": "capture", "meanings": ["bắt giữ", "nắm bắt"], "phonetic": "/ˈkæp.tʃər/", "word_class": "verb",
     "examples": [["The photo captured a perfect moment.", "Bức ảnh nắm bắt được một khoảnh khắc hoàn hảo."]]},
    {"word": "celebrate", "meanings": ["kỷ niệm", "tổ chức lễ"], "phonetic": "/ˈsel.ɪ.breɪt/", "word_class": "verb",
     "examples": [["They celebrated their anniversary.", "Họ kỷ niệm ngày cưới của mình."]]},
    {"word": "challenge", "meanings": ["thách thức", "thử thách"], "phonetic": "/ˈtʃæl.ɪndʒ/", "word_class": "noun",
     "examples": [["Every challenge is an opportunity.", "Mỗi thách thức là một cơ hội."]]},
    {"word": "change", "meanings": ["thay đổi", "biến đổi"], "phonetic": "/tʃeɪndʒ/", "word_class": "verb",
     "examples": [["Change is inevitable.", "Sự thay đổi là không thể tránh khỏi."]]},
    {"word": "character", "meanings": ["tính cách", "nhân vật", "chữ cái"], "phonetic": "/ˈkær.ɪk.tər/", "word_class": "noun",
     "examples": [["His character is admirable.", "Tính cách của anh ấy đáng ngưỡng mộ."]]},
    {"word": "communicate", "meanings": ["giao tiếp", "truyền đạt"], "phonetic": "/kəˈmjuː.nɪ.keɪt/", "word_class": "verb",
     "examples": [["It is important to communicate clearly.", "Giao tiếp rõ ràng là điều quan trọng."]]},
    {"word": "community", "meanings": ["cộng đồng", "xã hội", "khu dân cư"], "phonetic": "/kəˈmjuː.nɪ.ti/", "word_class": "noun",
     "examples": [["She is active in her local community.", "Cô ấy tích cực trong cộng đồng địa phương của mình."]]},
    {"word": "complex", "meanings": ["phức tạp", "tổ hợp"], "phonetic": "/ˈkɒm.pleks/", "word_class": "adjective",
     "examples": [["This is a complex problem.", "Đây là một vấn đề phức tạp."]]},
    {"word": "concept", "meanings": ["khái niệm", "ý tưởng"], "phonetic": "/ˈkɒn.sept/", "word_class": "noun",
     "examples": [["The concept of time is fascinating.", "Khái niệm về thời gian rất thú vị."]]},
    {"word": "confidence", "meanings": ["sự tự tin", "lòng tin"], "phonetic": "/ˈkɒn.fɪ.dəns/", "word_class": "noun",
     "examples": [["Confidence is key to success.", "Sự tự tin là chìa khóa thành công."]]},
    {"word": "create", "meanings": ["tạo ra", "sáng tạo"], "phonetic": "/kriˈeɪt/", "word_class": "verb",
     "examples": [["Artists create beautiful works.", "Nghệ sĩ tạo ra những tác phẩm đẹp."]]},
    {"word": "culture", "meanings": ["văn hóa", "nền văn minh"], "phonetic": "/ˈkʌl.tʃər/", "word_class": "noun",
     "examples": [["Every country has its own culture.", "Mỗi quốc gia đều có nền văn hóa riêng."]]},
    {"word": "curious", "meanings": ["tò mò", "hiếu kỳ"], "phonetic": "/ˈkjʊə.ri.əs/", "word_class": "adjective",
     "examples": [["Children are naturally curious.", "Trẻ em tự nhiên tò mò."]]},
    {"word": "danger", "meanings": ["nguy hiểm", "mối đe dọa"], "phonetic": "/ˈdeɪn.dʒər/", "word_class": "noun",
     "examples": [["They were in great danger.", "Họ đang trong tình trạng nguy hiểm cực độ."]]},
    {"word": "decide", "meanings": ["quyết định", "giải quyết"], "phonetic": "/dɪˈsaɪd/", "word_class": "verb",
     "examples": [["It is hard to decide which path to take.", "Thật khó để quyết định đi theo con đường nào."]]},
    {"word": "definition", "meanings": ["định nghĩa", "khái niệm"], "phonetic": "/ˌdef.ɪˈnɪʃ.ən/", "word_class": "noun",
     "examples": [["What is the definition of success?", "Định nghĩa của thành công là gì?"]]},
    {"word": "depend", "meanings": ["phụ thuộc", "dựa vào"], "phonetic": "/dɪˈpend/", "word_class": "verb",
     "examples": [["Success depends on hard work.", "Thành công phụ thuộc vào sự chăm chỉ."]]},
    {"word": "describe", "meanings": ["mô tả", "miêu tả"], "phonetic": "/dɪˈskraɪb/", "word_class": "verb",
     "examples": [["Can you describe the incident?", "Bạn có thể mô tả sự việc không?"]]},
    {"word": "develop", "meanings": ["phát triển", "xây dựng"], "phonetic": "/dɪˈvel.əp/", "word_class": "verb",
     "examples": [["We develop new skills over time.", "Chúng ta phát triển kỹ năng mới theo thời gian."]]},
    {"word": "dictionary", "meanings": ["từ điển", "tự điển"], "phonetic": "/ˈdɪk.ʃən.ri/", "word_class": "noun",
     "examples": [["A dictionary is a useful tool.", "Từ điển là một công cụ hữu ích."]]},
    {"word": "discover", "meanings": ["khám phá", "phát hiện"], "phonetic": "/dɪˈskʌv.ər/", "word_class": "verb",
     "examples": [["Scientists discover new things every day.", "Các nhà khoa học khám phá những điều mới mỗi ngày."]]},
    {"word": "education", "meanings": ["giáo dục", "học vấn"], "phonetic": "/ˌedʒ.uˈkeɪ.ʃən/", "word_class": "noun",
     "examples": [["Education is the key to the future.", "Giáo dục là chìa khóa của tương lai."]]},
    {"word": "efficient", "meanings": ["hiệu quả", "hiệu suất cao"], "phonetic": "/ɪˈfɪʃ.ənt/", "word_class": "adjective",
     "examples": [["This engine is very efficient.", "Động cơ này rất hiệu quả."]]},
    {"word": "emotion", "meanings": ["cảm xúc", "tình cảm"], "phonetic": "/ɪˈməʊ.ʃən/", "word_class": "noun",
     "examples": [["Music can evoke strong emotions.", "Âm nhạc có thể gợi lên cảm xúc mạnh mẽ."]]},
    {"word": "encourage", "meanings": ["khuyến khích", "động viên"], "phonetic": "/ɪnˈkʌr.ɪdʒ/", "word_class": "verb",
     "examples": [["Parents encourage their children.", "Cha mẹ động viên con cái của họ."]]},
    {"word": "environment", "meanings": ["môi trường", "môi sinh"], "phonetic": "/ɪnˈvaɪ.rən.mənt/", "word_class": "noun",
     "examples": [["We must protect the environment.", "Chúng ta phải bảo vệ môi trường."]]},
    {"word": "essential", "meanings": ["thiết yếu", "cơ bản", "quan trọng"], "phonetic": "/ɪˈsen.ʃəl/", "word_class": "adjective",
     "examples": [["Water is essential for life.", "Nước rất thiết yếu cho sự sống."]]},
    {"word": "evidence", "meanings": ["bằng chứng", "chứng cứ"], "phonetic": "/ˈev.ɪ.dəns/", "word_class": "noun",
     "examples": [["The evidence proves his innocence.", "Bằng chứng chứng minh sự vô tội của anh ấy."]]},
    {"word": "examine", "meanings": ["kiểm tra", "xem xét", "khám bệnh"], "phonetic": "/ɪɡˈzæm.ɪn/", "word_class": "verb",
     "examples": [["The doctor examined the patient.", "Bác sĩ khám bệnh nhân."]]},
    {"word": "experience", "meanings": ["kinh nghiệm", "trải nghiệm"], "phonetic": "/ɪkˈspɪə.ri.əns/", "word_class": "noun",
     "examples": [["Experience is the best teacher.", "Kinh nghiệm là người thầy tốt nhất."]]},
    {"word": "explain", "meanings": ["giải thích", "làm rõ"], "phonetic": "/ɪkˈspleɪn/", "word_class": "verb",
     "examples": [["Please explain the process.", "Xin hãy giải thích quy trình."]]},
    {"word": "explore", "meanings": ["khám phá", "thăm dò"], "phonetic": "/ɪkˈsplɔːr/", "word_class": "verb",
     "examples": [["We love to explore new places.", "Chúng tôi thích khám phá những nơi mới."]]},
    {"word": "failure", "meanings": ["thất bại", "sự thất bại"], "phonetic": "/ˈfeɪ.ljər/", "word_class": "noun",
     "examples": [["Failure is a stepping stone to success.", "Thất bại là bước đệm đến thành công."]]},
    {"word": "finance", "meanings": ["tài chính", "nguồn vốn"], "phonetic": "/ˈfaɪ.næns/", "word_class": "noun",
     "examples": [["Good finance management is important.", "Quản lý tài chính tốt là điều quan trọng."]]},
    {"word": "flexible", "meanings": ["linh hoạt", "dễ uốn"], "phonetic": "/ˈflek.sɪ.bəl/", "word_class": "adjective",
     "examples": [["A flexible schedule helps work-life balance.", "Lịch trình linh hoạt giúp cân bằng cuộc sống."]]},
    {"word": "focus", "meanings": ["tập trung", "trọng tâm"], "phonetic": "/ˈfəʊ.kəs/", "word_class": "verb",
     "examples": [["Focus on your goals.", "Tập trung vào mục tiêu của bạn."]]},
    {"word": "freedom", "meanings": ["tự do", "quyền tự do"], "phonetic": "/ˈfriː.dəm/", "word_class": "noun",
     "examples": [["Freedom is a fundamental right.", "Tự do là quyền cơ bản."]]},
    {"word": "future", "meanings": ["tương lai", "thì tương lai"], "phonetic": "/ˈfjuː.tʃər/", "word_class": "noun",
     "examples": [["The future belongs to those who prepare.", "Tương lai thuộc về những người chuẩn bị."]]},
    {"word": "generate", "meanings": ["tạo ra", "sản sinh"], "phonetic": "/ˈdʒen.ər.eɪt/", "word_class": "verb",
     "examples": [["Solar panels generate electricity.", "Pin mặt trời tạo ra điện."]]},
    {"word": "genuine", "meanings": ["thật sự", "chân thật", "chính hãng"], "phonetic": "/ˈdʒen.ju.ɪn/", "word_class": "adjective",
     "examples": [["She showed genuine concern.", "Cô ấy bày tỏ sự quan tâm chân thật."]]},
    {"word": "global", "meanings": ["toàn cầu", "thế giới"], "phonetic": "/ˈɡləʊ.bəl/", "word_class": "adjective",
     "examples": [["Climate change is a global problem.", "Biến đổi khí hậu là vấn đề toàn cầu."]]},
    {"word": "harmony", "meanings": ["sự hòa hợp", "hòa âm"], "phonetic": "/ˈhɑː.mə.ni/", "word_class": "noun",
     "examples": [["They lived in harmony with nature.", "Họ sống hòa hợp với thiên nhiên."]]},
    {"word": "history", "meanings": ["lịch sử", "tiểu sử"], "phonetic": "/ˈhɪs.tər.i/", "word_class": "noun",
     "examples": [["History teaches us important lessons.", "Lịch sử dạy chúng ta những bài học quan trọng."]]},
    {"word": "human", "meanings": ["con người", "thuộc con người"], "phonetic": "/ˈhjuː.mən/", "word_class": "noun",
     "examples": [["All humans deserve respect.", "Mọi con người đều xứng đáng được tôn trọng."]]},
    {"word": "identify", "meanings": ["nhận dạng", "xác định", "tìm ra"], "phonetic": "/aɪˈden.tɪ.faɪ/", "word_class": "verb",
     "examples": [["Can you identify the problem?", "Bạn có thể xác định vấn đề không?"]]},
    {"word": "imagine", "meanings": ["tưởng tượng", "hình dung"], "phonetic": "/ɪˈmædʒ.ɪn/", "word_class": "verb",
     "examples": [["Imagine a world without pollution.", "Hãy tưởng tượng một thế giới không có ô nhiễm."]]},
    {"word": "improve", "meanings": ["cải thiện", "nâng cao"], "phonetic": "/ɪmˈpruːv/", "word_class": "verb",
     "examples": [["Practice helps you improve.", "Luyện tập giúp bạn cải thiện."]]},
    {"word": "independent", "meanings": ["độc lập", "tự lập"], "phonetic": "/ˌɪn.dɪˈpen.dənt/", "word_class": "adjective",
     "examples": [["She became financially independent.", "Cô ấy trở nên độc lập về tài chính."]]},
    {"word": "influence", "meanings": ["ảnh hưởng", "tác động"], "phonetic": "/ˈɪn.flu.əns/", "word_class": "noun",
     "examples": [["Parents have great influence on children.", "Cha mẹ có ảnh hưởng lớn đến con cái."]]},
    {"word": "innovation", "meanings": ["đổi mới", "sáng tạo", "cải tiến"], "phonetic": "/ˌɪn.əˈveɪ.ʃən/", "word_class": "noun",
     "examples": [["Innovation drives economic growth.", "Đổi mới thúc đẩy tăng trưởng kinh tế."]]},
    {"word": "inspire", "meanings": ["truyền cảm hứng", "khích lệ"], "phonetic": "/ɪnˈspaɪər/", "word_class": "verb",
     "examples": [["Her story inspired thousands.", "Câu chuyện của cô ấy truyền cảm hứng cho hàng ngàn người."]]},
    {"word": "intelligence", "meanings": ["trí thông minh", "tình báo"], "phonetic": "/ɪnˈtel.ɪ.dʒəns/", "word_class": "noun",
     "examples": [["Artificial intelligence is transforming industries.", "Trí tuệ nhân tạo đang thay đổi các ngành công nghiệp."]]},
    {"word": "journey", "meanings": ["hành trình", "chuyến đi"], "phonetic": "/ˈdʒɜː.ni/", "word_class": "noun",
     "examples": [["Life is a wonderful journey.", "Cuộc sống là một hành trình tuyệt vời."]]},
    {"word": "justice", "meanings": ["công lý", "sự công bằng"], "phonetic": "/ˈdʒʌs.tɪs/", "word_class": "noun",
     "examples": [["Justice must be served.", "Công lý phải được thực thi."]]},
    {"word": "knowledge", "meanings": ["kiến thức", "tri thức"], "phonetic": "/ˈnɒl.ɪdʒ/", "word_class": "noun",
     "examples": [["Knowledge is power.", "Kiến thức là sức mạnh."]]},
    {"word": "language", "meanings": ["ngôn ngữ", "lời nói"], "phonetic": "/ˈlæŋ.ɡwɪdʒ/", "word_class": "noun",
     "examples": [["Learning a new language opens doors.", "Học một ngôn ngữ mới mở ra nhiều cơ hội."]]},
    {"word": "leader", "meanings": ["người lãnh đạo", "thủ lĩnh"], "phonetic": "/ˈliː.dər/", "word_class": "noun",
     "examples": [["A good leader listens to their team.", "Một nhà lãnh đạo tốt lắng nghe đội nhóm của họ."]]},
    {"word": "literature", "meanings": ["văn học", "tài liệu"], "phonetic": "/ˈlɪt.rɪ.tʃər/", "word_class": "noun",
     "examples": [["Literature reflects society.", "Văn học phản ánh xã hội."]]},
    {"word": "manage", "meanings": ["quản lý", "xoay sở"], "phonetic": "/ˈmæn.ɪdʒ/", "word_class": "verb",
     "examples": [["She manages a team of ten people.", "Cô ấy quản lý một nhóm mười người."]]},
    {"word": "memory", "meanings": ["ký ức", "bộ nhớ"], "phonetic": "/ˈmem.ər.i/", "word_class": "noun",
     "examples": [["That song brings back memories.", "Bài hát đó gợi lại ký ức."]]},
    {"word": "method", "meanings": ["phương pháp", "cách thức"], "phonetic": "/ˈmeθ.əd/", "word_class": "noun",
     "examples": [["This method is more efficient.", "Phương pháp này hiệu quả hơn."]]},
    {"word": "mountain", "meanings": ["núi", "dãy núi"], "phonetic": "/ˈmaʊn.tɪn/", "word_class": "noun",
     "examples": [["They climbed the mountain together.", "Họ leo núi cùng nhau."]]},
    {"word": "nature", "meanings": ["thiên nhiên", "bản chất"], "phonetic": "/ˈneɪ.tʃər/", "word_class": "noun",
     "examples": [["Spending time in nature reduces stress.", "Dành thời gian trong thiên nhiên giúp giảm căng thẳng."]]},
    {"word": "opportunity", "meanings": ["cơ hội", "dịp"], "phonetic": "/ˌɒp.əˈtjuː.nɪ.ti/", "word_class": "noun",
     "examples": [["Every difficulty hides an opportunity.", "Mỗi khó khăn ẩn chứa một cơ hội."]]},
    {"word": "passion", "meanings": ["đam mê", "nhiệt huyết"], "phonetic": "/ˈpæʃ.ən/", "word_class": "noun",
     "examples": [["Follow your passion.", "Hãy theo đuổi đam mê của bạn."]]},
    {"word": "patient", "meanings": ["kiên nhẫn", "bệnh nhân"], "phonetic": "/ˈpeɪ.ʃənt/", "word_class": "adjective",
     "examples": [["Be patient — good things take time.", "Hãy kiên nhẫn — những điều tốt cần có thời gian."]]},
    {"word": "persistent", "meanings": ["kiên trì", "bền bỉ"], "phonetic": "/pəˈsɪs.tənt/", "word_class": "adjective",
     "examples": [["Persistent effort leads to success.", "Nỗ lực kiên trì dẫn đến thành công."]]},
    {"word": "philosophy", "meanings": ["triết học", "triết lý"], "phonetic": "/fɪˈlɒs.ə.fi/", "word_class": "noun",
     "examples": [["Philosophy encourages deep thinking.", "Triết học khuyến khích tư duy sâu sắc."]]},
    {"word": "practice", "meanings": ["thực hành", "luyện tập"], "phonetic": "/ˈpræk.tɪs/", "word_class": "noun",
     "examples": [["Practice makes perfect.", "Luyện tập tạo nên sự hoàn hảo."]]},
    {"word": "progress", "meanings": ["tiến bộ", "phát triển"], "phonetic": "/ˈprəʊ.ɡres/", "word_class": "noun",
     "examples": [["The project is making great progress.", "Dự án đang có tiến triển tốt."]]},
    {"word": "quality", "meanings": ["chất lượng", "phẩm chất"], "phonetic": "/ˈkwɒl.ɪ.ti/", "word_class": "noun",
     "examples": [["Quality is more important than quantity.", "Chất lượng quan trọng hơn số lượng."]]},
    {"word": "realize", "meanings": ["nhận ra", "hiểu được", "thực hiện"], "phonetic": "/ˈrɪə.laɪz/", "word_class": "verb",
     "examples": [["I realized my mistake too late.", "Tôi nhận ra lỗi lầm của mình quá muộn."]]},
    {"word": "research", "meanings": ["nghiên cứu", "tìm hiểu"], "phonetic": "/rɪˈsɜːtʃ/", "word_class": "noun",
     "examples": [["Research is essential in science.", "Nghiên cứu là điều cần thiết trong khoa học."]]},
    {"word": "responsibility", "meanings": ["trách nhiệm", "nghĩa vụ"], "phonetic": "/rɪˌspɒn.sɪˈbɪl.ɪ.ti/", "word_class": "noun",
     "examples": [["With great power comes great responsibility.", "Quyền lực lớn đi kèm trách nhiệm lớn."]]},
    {"word": "solution", "meanings": ["giải pháp", "lời giải"], "phonetic": "/səˈluː.ʃən/", "word_class": "noun",
     "examples": [["Every problem has a solution.", "Mọi vấn đề đều có giải pháp."]]},
    {"word": "strategy", "meanings": ["chiến lược", "kế hoạch"], "phonetic": "/ˈstræt.ɪ.dʒi/", "word_class": "noun",
     "examples": [["A clear strategy is needed.", "Cần có một chiến lược rõ ràng."]]},
    {"word": "success", "meanings": ["thành công", "sự thành đạt"], "phonetic": "/səkˈses/", "word_class": "noun",
     "examples": [["Success is the result of hard work.", "Thành công là kết quả của sự chăm chỉ."]]},
    {"word": "technology", "meanings": ["công nghệ", "kỹ thuật"], "phonetic": "/tekˈnɒl.ə.dʒi/", "word_class": "noun",
     "examples": [["Technology changes our daily lives.", "Công nghệ thay đổi cuộc sống hàng ngày của chúng ta."]]},
    {"word": "tradition", "meanings": ["truyền thống", "phong tục"], "phonetic": "/trəˈdɪʃ.ən/", "word_class": "noun",
     "examples": [["We should respect cultural traditions.", "Chúng ta nên tôn trọng truyền thống văn hóa."]]},
    {"word": "transform", "meanings": ["biến đổi", "chuyển hóa"], "phonetic": "/trænsˈfɔːm/", "word_class": "verb",
     "examples": [["Education can transform lives.", "Giáo dục có thể thay đổi cuộc sống."]]},
    {"word": "understand", "meanings": ["hiểu", "thấu hiểu"], "phonetic": "/ˌʌn.dəˈstænd/", "word_class": "verb",
     "examples": [["It is important to understand others.", "Hiểu người khác là điều quan trọng."]]},
    {"word": "unique", "meanings": ["độc đáo", "duy nhất"], "phonetic": "/juˈniːk/", "word_class": "adjective",
     "examples": [["Everyone is unique in their own way.", "Mỗi người đều độc đáo theo cách riêng của họ."]]},
    {"word": "value", "meanings": ["giá trị", "đánh giá"], "phonetic": "/ˈvæl.juː/", "word_class": "noun",
     "examples": [["Family is the most important value.", "Gia đình là giá trị quan trọng nhất."]]},
    {"word": "vision", "meanings": ["tầm nhìn", "thị lực", "viễn cảnh"], "phonetic": "/ˈvɪʒ.ən/", "word_class": "noun",
     "examples": [["Great leaders have a clear vision.", "Những nhà lãnh đạo vĩ đại có tầm nhìn rõ ràng."]]},
    {"word": "wisdom", "meanings": ["sự khôn ngoan", "trí tuệ"], "phonetic": "/ˈwɪz.dəm/", "word_class": "noun",
     "examples": [["Wisdom comes with experience.", "Sự khôn ngoan đến theo kinh nghiệm."]]},
    {"word": "wonder", "meanings": ["kỳ diệu", "ngạc nhiên", "tự hỏi"], "phonetic": "/ˈwʌn.dər/", "word_class": "noun",
     "examples": [["The world is full of wonder.", "Thế giới đầy những điều kỳ diệu."]]},
]


# ── Helpers ────────────────────────────────────────────────────────────────

def _format_record(word: str, offset: int, length: int) -> bytes:
    """Build one 53-byte fixed-width index record."""
    key_bytes = word.lower().encode("utf-8", errors="replace")[:KEY_WIDTH]  # type: ignore
    key_bytes = key_bytes.ljust(KEY_WIDTH, b" ")
    off_bytes = str(offset).zfill(OFF_WIDTH).encode("ascii")
    len_bytes = str(length).zfill(LEN_WIDTH).encode("ascii")
    return key_bytes + off_bytes + len_bytes + b"\n"


def load_external_csv(master: dict, csv_path: str) -> None:
    """Merge an external CSV (columns: word, meaning) into master dict."""
    if not os.path.exists(csv_path):
        return
    print(f"  [CSV] Loading {csv_path} …")
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word    = row.get("word", "").lower().strip()
            meaning = row.get("meaning", "").strip()
            if word and meaning:
                if word not in master:
                    master[word] = {
                        "word": word, "meanings": [], "phonetic": "",
                        "word_class": "", "examples": []
                    }
                if meaning not in master[word]["meanings"]:
                    master[word]["meanings"].append(meaning)


def load_external_ipa(master: dict, ipa_path: str) -> None:
    """Merge IPA JSON (format: {word: /ɪpɑː/}) into master dict."""
    if not os.path.exists(ipa_path):
        return
    print(f"  [IPA] Loading {ipa_path} …")
    with open(ipa_path, encoding="utf-8") as f:
        ipa_data = json.load(f)
    for word, ipa in ipa_data.items():
        word = word.lower().strip()
        if word in master and not master[word]["phonetic"]:
            master[word]["phonetic"] = ipa


def load_external_tatoeba(master: dict, tsv_path: str) -> None:
    """Add sentence examples from Tatoeba TSV (format: EN\tVI)."""
    if not os.path.exists(tsv_path):
        return
    print(f"  [Tatoeba] Loading {tsv_path} …")
    with open(tsv_path, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            en, vi = parts[0].strip(), parts[1].strip()
            words_in_sentence = en.lower().split()
            for word in master:
                if word in words_in_sentence and len(master[word]["examples"]) < 3: # type: ignore
                    pair = [en, vi]
                    if pair not in master[word]["examples"]: # type: ignore
                        master[word]["examples"].append(pair) # type: ignore


# ── Main Pipeline ──────────────────────────────────────────────────────────

def build() -> None:
    """Run the full ETL pipeline."""
    print("=" * 60)
    print("Dictionary Builder — ETL Pipeline")
    print("=" * 60)

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)

    # ── 1. EXTRACT ──────────────────────────────────────────────────────
    print("\n[1] EXTRACT — Loading sample data …")
    master: dict = {} # type: ignore
    for item in SAMPLE_DATA:
        word = item["word"].lower().strip() # type: ignore
        master[word] = item.copy()

    print(f"  Loaded {len(master)} embedded entries.")

    # Optionally merge external sources if present
    full_json = os.path.join(RAW_DIR, "full_dict.json")
    if os.path.exists(full_json):
        print(f"  [JSON] Loading rich dictionary from {full_json} ...")
        with open(full_json, "r", encoding="utf-8") as f:
            rich_data = json.load(f)
            master.update(rich_data)
        print(f"  Merged {len(rich_data)} rich entries.")
    else:
        load_external_csv(master, os.path.join(RAW_DIR, "en_vi.csv"))
        load_external_ipa(master, os.path.join(RAW_DIR, "ipa.json"))
        load_external_tatoeba(master, os.path.join(RAW_DIR, "tatoeba.tsv"))

    # ── 2. TRANSFORM — Sort alphabetically ─────────────────────────────
    print(f"\n[2] TRANSFORM — Sorting {len(master)} entries alphabetically …")
    sorted_words = sorted(master.keys())

    # ── 3. LOAD — Write meaning.data + index.data ───────────────────────
    print(f"\n[3] LOAD — Writing binary data files …")

    with open(MEANING_FILE, "wb") as mf, \
         open(INDEX_FILE, "wb") as idxf:

        current_offset = 0

        for word in sorted_words:
            entry_data = master[word]

            payload = {
                "word":       entry_data.get("word", word),
                "meanings":   entry_data.get("meanings", []),
                "phonetic":   entry_data.get("phonetic", ""),
                "word_class": entry_data.get("word_class", ""),
                "examples":   entry_data.get("examples", []),
            }

            # Serialize to UTF-8 bytes (Vietnamese chars may be multi-byte)
            json_str   = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            json_bytes = json_str.encode("utf-8")
            length     = len(json_bytes)       # byte-length, not char-length!

            # Write meaning
            mf.write(json_bytes)

            # Write 53-byte index record
            record = _format_record(word, current_offset, length)
            assert len(record) == RECORD_SIZE, (
                f"Record for '{word}' is {len(record)} bytes, expected {RECORD_SIZE}"
            )
            idxf.write(record)

            current_offset += length

    total = len(sorted_words)
    idx_size = os.path.getsize(INDEX_FILE)
    data_size = os.path.getsize(MEANING_FILE)

    print(f"\n[OK] Built {total} entries")
    print(f"  meaning.data : {data_size:,} bytes")
    print(f"  index.data   : {idx_size:,} bytes ({idx_size // RECORD_SIZE} records x {RECORD_SIZE} bytes)")
    assert idx_size % RECORD_SIZE == 0, "ERROR: index.data has incorrect size!"
    print(f"\n[OK] Index integrity check PASSED — all records are {RECORD_SIZE} bytes wide")
    print("\n  Done! Run  python gui.py  to start the application.")


if __name__ == "__main__":
    build()

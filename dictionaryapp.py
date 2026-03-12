INDEX_FILE = "index.data"
MEANING_FILE = "meaning.data"


# ==================== ADD WORD ====================
def add_word():
    word = input("Enter word: ").strip()
    meaning = input("Enter meaning: ").strip()

    if word == "" or meaning == "":
        print("Word or meaning cannot be empty!")
        return

    meaning_bytes = meaning.encode("utf-8")
    length = len(meaning_bytes)

    # Get current end position of meaning.data
    f = open(MEANING_FILE, "ab")
    f.seek(0, 2)
    position = f.tell()
    f.close()

    # Check if word already exists in index.data
    f = open(INDEX_FILE, "a+", encoding="utf-8")
    f.seek(0)
    content = f.read()
    f.close()

    lines = content.split("\n")
    already_exists = False

    for line in lines:
        line = line.strip()
        if line == "":
            continue
        parts = line.split(";")
        if parts[0] == word:
            already_exists = True

    if already_exists:
        print("Word '" + word + "' already exists in dictionary!")
        return

    # Write meaning to meaning.data
    f = open(MEANING_FILE, "ab")
    f.write(meaning_bytes)
    f.close()

    # Write index to index.data
    f = open(INDEX_FILE, "a", encoding="utf-8")
    f.write(word + ";" + str(position) + ";" + str(length) + "\n")
    f.close()

    print("Added: '" + word + "' -> '" + meaning + "' (position: " + str(position) + ", length: " + str(length) + " bytes)")


# ==================== SEARCH WORD ====================
def search_word():
    word = input("Enter word to search: ").strip()

    if word == "":
        print("Please enter a word!")
        return

    # Read index.data
    f = open(INDEX_FILE, "r", encoding="utf-8")
    content = f.read()
    f.close()

    lines = content.split("\n")
    found = False

    for line in lines:
        line = line.strip()
        if line == "":
            continue
        parts = line.split(";")
        if len(parts) != 3:
            continue

        if parts[0] == word:
            position = int(parts[1])
            length = int(parts[2])

            # Read meaning from meaning.data
            f = open(MEANING_FILE, "rb")
            f.seek(position, 0)
            meaning_bytes = f.read(length)
            f.close()

            meaning = meaning_bytes.decode("utf-8")
            print(word + ": " + meaning)
            found = True

    if found == False:
        print("Word '" + word + "' not found in dictionary!")


# ==================== MAIN ====================
def main():
    print("===========================")
    print("     SIMPLE DICTIONARY     ")
    print("===========================")

    # Create files if not exist
    f = open(INDEX_FILE, "a", encoding="utf-8")
    f.close()
    f = open(MEANING_FILE, "ab")
    f.close()

    running = True

    while running:
        print("\n1. Add word")
        print("2. Search word")
        print("3. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            add_word()
        elif choice == "2":
            search_word()
        elif choice == "3":
            print("Goodbye!")
            running = False
        else:
            print("Please choose 1, 2 or 3!")


main()
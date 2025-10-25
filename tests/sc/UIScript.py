import os

def append_files(file_list_path, output_path):
    """
    Reads a list of text file paths from `file_list_path`
    and appends all their contents into `output_path`.
    """

    # Delete existing output file
    if os.path.exists(output_path):
        os.remove(output_path)
        print(f"🗑️ Existing file deleted: {output_path}")

    # Read the input list file
    with open(file_list_path, "r", encoding="utf-8") as list_file:
        file_paths = [line.strip() for line in list_file if line.strip()]
    with open(output_path, "w", encoding="utf-8") as outfile:
        for path in file_paths:
            if not os.path.isfile(path):
                outfile.write(f"⚠️ File not found: {path}\n")
                outfile.write("-" * 60 + "\n\n")
                continue

            filename = os.path.basename(path)
            outfile.write(f"Below is file content of: {filename}\n")
            outfile.write("-" * 60 + "\n")

            with open(path, "r", encoding="utf-8") as infile:
                outfile.write(infile.read().rstrip() + "\n\n")

    print(f"✅ All files appended successfully into: {output_path}")


if __name__ == "__main__":
    # Example usage:
    file_list = "D:\\Working\\AI\\WH Face Detection\\tests\\sc\\UIList.txt"
    output_file = "D:\\abc.txt"
    append_files(file_list, output_file)

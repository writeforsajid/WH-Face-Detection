import os
import shutil
import subprocess
from typing import Optional, List, Dict
import time


class FileManager:
    """
    A utility class for file and folder operations, including JPEG metadata management
    and safe deletion of files or directories.
    """

    # -------------------- JPEG Metadata --------------------

    
    def write_custom_property(image_path: str, property_name: str, value: str) -> bool:
        """
        Write a custom metadata property (XMP) to a JPEG image without re-encoding it.

        Returns:
            True if successful, False otherwise.
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"File not found: {image_path}")

            result = subprocess.run(
                [
                    "exiftool",
                    f"-XMP:{property_name}={value}",
                    "-overwrite_original",
                    image_path
                ],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError(f"Exiftool error: {result.stderr.strip()}")

            return True

        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
        except subprocess.SubprocessError as e:
            print(f"❌ Subprocess error while writing metadata: {e}")
        except Exception as e:
            print(f"❌ Unexpected error writing metadata: {e}")
        return False

    # --------------------------------------------------------

    
    def read_custom_property(image_path: str, property_name: str) -> Optional[str]:
        """
        Read a custom metadata property (XMP) from a JPEG image.
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"File not found: {image_path}")

            result = subprocess.run(
                ["exiftool", f"-XMP:{property_name}", "-b", image_path],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode != 0:
                raise RuntimeError(f"Exiftool error: {result.stderr.strip()}")

            value = result.stdout.strip()
            return value if value else None

        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
        except subprocess.SubprocessError as e:
            print(f"❌ Subprocess error while reading metadata: {e}")
        except Exception as e:
            print(f"❌ Unexpected error reading metadata: {e}")
        return None

    # -------------------- File Deletion --------------------

    
    def delete_all_files_and_subfolders(folder_path: str) -> bool:
        """Delete all files and subfolders inside the given folder."""
        try:
            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"Folder not found: {folder_path}")

            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

            print(f"✅ Deleted all contents of folder: {folder_path}")
            return True

        except Exception as e:
            print(f"❌ Error deleting folder contents: {e}")
            return False

    # --------------------------------------------------------

    
    def delete_all_files_only(folder_path: str) -> bool:
        """Delete all files (but not subfolders) in the given folder."""
        try:
            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"Folder not found: {folder_path}")

            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)

            print(f"✅ Deleted all files in: {folder_path}")
            return True

        except Exception as e:
            print(f"❌ Error deleting files in folder: {e}")
            return False

    # --------------------------------------------------------

    
    def delete_files_from_list(file_list: List[Dict]) -> None:
        """Delete all files whose paths are provided in the list of dictionaries."""
        if not isinstance(file_list, list):
            print("❌ Error: file_list must be a list of dictionaries")
            return

        for item in file_list:
            try:
                if not isinstance(item, dict) or "path" not in item:
                    print(f"⚠️ Skipping invalid entry: {item}")
                    continue

                file_path = item["path"]
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    os.remove(file_path)
                    #print(f"🗑️ Deleted: {file_path}")
                else:
                    print(f"⚠️ File not found or invalid: {file_path}")

            except Exception as e:
                print(f"❌ Error deleting {item.get('path', 'unknown')}: {e}")

    # --------------------------------------------------------

    
    def delete_folder_and_all_contents(folder_path: str) -> bool:
        """Delete the folder itself and everything inside it."""
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                print(f"🗑️ Deleted folder and all contents: {folder_path}")
                return True
            else:
                print(f"⚠️ Folder not found: {folder_path}")
                return False
        except Exception as e:
            print(f"❌ Error deleting folder {folder_path}: {e}")
            return False

    def delete_old_files(base_path, minutes=120):
        """
        Deletes all files and folders inside `base_path` that were last modified
        more than `minutes` ago.
        """
        if not os.path.exists(base_path):
            print(f"[WARN] Path not found: {base_path}")
            return

        cutoff_time = time.time() - (minutes * 60)
        deleted_count = 0

        for root, dirs, files in os.walk(base_path, topdown=False):
            # Delete old files
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        #print(f"[INFO] Deleted file: {file_path}")
                except Exception as e:
                    print(f"[ERROR] Could not delete file {file_path}: {e}")

            # Delete old empty folders
            for name in dirs:
                dir_path = os.path.join(root, name)
                try:
                    if os.path.getmtime(dir_path) < cutoff_time and not os.listdir(dir_path):
                        shutil.rmtree(dir_path)
                        deleted_count += 1
                        print(f"[INFO] Deleted folder: {dir_path}")
                except Exception as e:
                    print(f"[ERROR] Could not delete folder {dir_path}: {e}")

        if deleted_count == 0:
            print("[INFO] No old files or folders found.")
        else:
            print(f"[DONE] Deleted {deleted_count} old files/folders.")
import argparse
import codecs
import os
import re
import sys


def optimize_date(markdown_content):
    """
    Optimizes specific Markdown patterns, e.g., a custom date format.
    """
    # Pattern for:
    # Optional leading whitespace
    # DD
    #
    # MM
    #
    # DAY_OF_WEEK
    #
    #  ____
    #
    #   * __ (four times)
    # (one empty line)
    #   * __ (four times)
    # Replaces with DD/MM/DAY_OF_WEEK
    # Adjusted pattern based on repr output:
    # - Added \s* at the beginning for leading whitespace (and BOM if not handled by utf-8-sig)
    # - Changed separator between the two '* __' blocks from \n to \n\n
    pattern = r"\s*(\d+)\n\n(\d+)\n\n([^\n]+)\n\n[ \t]*____[ \t]*\n\n(?:[ \t]*\*[ \t]*__[ \t]*\n){4}\n\n(?:[ \t]*\*[ \t]*__[ \t]*\n){3}[ \t]*\*[ \t]*__[ \t]*"
    replacement = r"\1/\2/\3"
    
    optimized_content, num_replacements = re.subn(pattern, replacement, markdown_content)
    
    if num_replacements == 0:
        # Debug print if no replacements were made
        print(f"DEBUG: Pattern did not match. Content start (repr): {repr(markdown_content[:500])}")
        # You can also print the full repr(markdown_content) if needed, or write it to a debug file.
        # print(f"DEBUG: Full pattern used: {pattern}")

    # if num_replacements > 0:
    #     print(f"Optimized date format ({num_replacements} occurrence(s)).")
    return optimized_content, num_replacements

def process_markdown_file(file_path):
    """
    Reads a Markdown file, optimizes its content, adds a title if it's an index.md file, and writes it back.
    """
    try:
        # Try reading with UTF-8-SIG first to handle BOM, then fallback
        original_content_for_write_check = "" # Store content before any modification for accurate change detection
        try:
            # Use 'utf-8-sig' to automatically remove BOM
            with codecs.open(file_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                original_content_for_write_check = content
        except UnicodeDecodeError:
            print(f"Warning: UTF-8-SIG decoding failed for {file_path}. Trying utf-8.", file=sys.stderr)
            try:
                with codecs.open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    original_content_for_write_check = content
            except UnicodeDecodeError:
                print(f"Warning: UTF-8 decoding failed for {file_path}. Trying default encoding.", file=sys.stderr)
                # Use system's default encoding, ignore errors if it still fails
                with open(file_path, 'r', encoding=sys.getdefaultencoding(), errors='ignore') as f:
                    content = f.read()
                    original_content_for_write_check = content
        
        current_content = content
        made_changes = False

        # Optimize date format
        optimized_date_content, num_date_replacements = optimize_date(current_content)
        if num_date_replacements > 0:
            current_content = optimized_date_content
            made_changes = True
            print(f"Optimized date format in: {file_path} ({num_date_replacements} replacement(s))")

        # Add title for index.md files
        filename = os.path.basename(file_path)
        if filename.lower() == "index.md":
            parent_dir_name = os.path.basename(os.path.dirname(file_path))
            title_to_add = f"# {parent_dir_name}\n\n"
            # Check if title already exists to avoid duplication
            if not current_content.strip().startswith(f"# {parent_dir_name}"):
                current_content = title_to_add + current_content
                made_changes = True
                print(f"Added title to: {file_path}")
            else:
                print(f"Title already exists in: {file_path}")


        if made_changes:
            # Only write if content has actually changed from the initially read version
            # This check is more robust than just relying on num_replacements if multiple operations occur
            if current_content != original_content_for_write_check:
                 with codecs.open(file_path, 'w', encoding='utf-8') as f:
                    f.write(current_content)
            else:
                # This case might happen if, for example, a title was "added" but it was already there
                # and no date optimization occurred.
                print(f"No effective changes to write for: {file_path}")
        # else:
            # print(f"No changes needed for: {file_path}")

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
    except IOError as e:
        print(f"Error reading/writing file {file_path}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error processing file {file_path}: {e}", file=sys.stderr)

def process_directory_recursive(directory_path):
    """
    Recursively processes all .md files in a directory.
    """
    print(f"Starting recursive processing of directory: {directory_path}")
    file_count = 0
    optimized_files_count = 0

    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith(".md"):
                file_path = os.path.join(root, file)
                # Store original content to check if it changed, to count optimized files
                try:
                    with codecs.open(file_path, 'r', encoding='utf-8') as f_orig:
                        original_content = f_orig.read()
                except Exception: # Broad catch for reading issues, will be handled in process_markdown_file
                    original_content = "" 
                
                process_markdown_file(file_path)
                file_count += 1

                # Check if content was actually modified to count optimized files
                if original_content: # Only if we could read original content
                    try:
                        with codecs.open(file_path, 'r', encoding='utf-8') as f_new:
                            new_content = f_new.read()
                        if new_content != original_content:
                             optimized_files_count +=1
                    except Exception:
                        pass # Error reading new content, skip check

    print(f"Finished processing directory. Processed {file_count} .md files. Optimized {optimized_files_count} files.")

def main():
    """Main function to parse arguments and initiate processing."""
    parser = argparse.ArgumentParser(
        description="Recursively find and optimize Markdown files in a directory."
    )
    parser.add_argument("directory_path", help="Path to the directory containing Markdown files. If the path contains spaces or special characters, ensure it is properly quoted (e.g., enclosed in double quotes).")
    args = parser.parse_args()

    input_path = os.path.abspath(args.directory_path)

    if not os.path.isdir(input_path):
        print(f"Error: Input path is not a valid directory: {input_path}", file=sys.stderr)
        sys.exit(1)

    process_directory_recursive(input_path)
    print("Optimization complete.")

if __name__ == "__main__":
    main()

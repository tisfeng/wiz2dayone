import argparse
import codecs
import os
import re  # Added import
import subprocess  # Added import
import sys

# This script converts HTML files to Markdown format using the html2text library.
# It can process both single HTML files and directories containing HTML files,
# converting all HTML files within the directory structure to Markdown.
# The converted Markdown files are saved in a new directory named 'html2markdown'
# relative to the input path.
#
# Usage: python html2markdown.py <path_to_html_file_or_directory>

# Check for html2text dependency at the beginning
try:
    import html2text
except ImportError:
    print("Error: The 'html2text' library is required. Please install it using 'pip install html2text'", file=sys.stderr)
    sys.exit(1)

OUTPUT_DIR_NAME = "html2markdown"
UPIC_EXECUTABLE = "/Applications/uPic.app/Contents/MacOS/uPic"  # Path to uPic executable

def ensure_dir(directory):
    """Ensures that the specified directory exists, creating it if necessary."""
    os.makedirs(directory, exist_ok=True)

def upload_image_with_upic(local_image_path):
    """
    Uploads an image using uPic and returns the remote URL.
    Returns None if upload fails.
    """
    if not os.path.exists(local_image_path):
        print(f"Warning: Local image not found for upload: {local_image_path}", file=sys.stderr)
        return None

    try:
        # Ensure the uPic executable path is correct and uPic is installed.
        command = [UPIC_EXECUTABLE, "-u", local_image_path]
        print(f"Executing uPic command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        
        output_lines = result.stdout.splitlines()
        for line in output_lines:
            # uPic typically outputs the URL directly or after "Output URL:"
            if line.startswith("http://") or line.startswith("https://"):
                print(f"Successfully uploaded {local_image_path} to {line.strip()}")
                return line.strip()
        
        # Fallback for varied uPic outputs: search for URL in the entire output
        url_match = re.search(r'(https?://[^\s]+)', result.stdout)
        if url_match:
            url = url_match.group(0)
            print(f"Successfully uploaded (found via regex) {local_image_path} to {url}")
            return url

        print(f"Warning: Could not find URL in uPic output for {local_image_path}.\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print(f"Error: uPic executable not found at '{UPIC_EXECUTABLE}'. Please ensure uPic is installed and the path is correct.", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error during uPic execution for {local_image_path}: {e}\nStdout:\n{e.stdout}\nStderr:\n{e.stderr}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during uPic upload for {local_image_path}: {e}", file=sys.stderr)
        return None

def convert_html_to_markdown(input_file_path, output_file_path, converter):
    """
    Reads an HTML file, converts it to Markdown, uploads local images,
    and saves it to the output path.
    """
    try:
        # Try reading with UTF-8 first, fallback to default encoding with error handling
        try:
            with codecs.open(input_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        except UnicodeDecodeError:
            print(f"Warning: UTF-8 decoding failed for {input_file_path}. Trying default encoding.", file=sys.stderr)
            # Use system's default encoding, ignore errors if it still fails
            with open(input_file_path, 'r', encoding=sys.getdefaultencoding(), errors='ignore') as f:
                html_content = f.read()

        markdown_content = converter.handle(html_content)

        # Process local images in Markdown content
        html_file_dir = os.path.dirname(input_file_path)

        def replace_image_link(match):
            alt_text = match.group(1)
            image_path_in_md = match.group(2)

            # If already a web URL, do nothing
            if image_path_in_md.startswith("http://") or image_path_in_md.startswith("https://"):
                return match.group(0)  # Return the original full match

            # Construct absolute path for the local image
            # Image paths from HTML are relative to the HTML file's directory
            absolute_image_path = os.path.normpath(os.path.join(html_file_dir, image_path_in_md))
            
            if not os.path.exists(absolute_image_path):
                print(f"Warning: Image file not found at resolved path {absolute_image_path} (original: {image_path_in_md}). Keeping original path.", file=sys.stderr)
                return match.group(0)

            print(f"Found local image: {image_path_in_md}. Absolute path: {absolute_image_path}. Attempting upload...")
            remote_url = upload_image_with_upic(absolute_image_path)

            if remote_url:
                print(f"Replacing '{image_path_in_md}' with '{remote_url}'")
                return f"![{alt_text}]({remote_url})"
            else:
                print(f"Warning: Failed to upload {absolute_image_path}. Keeping local path '{image_path_in_md}'.", file=sys.stderr)
                return match.group(0)  # Fallback to original full match if upload fails

        # Regex to find Markdown image links: ![alt text](path)
        # It captures alt text in group 1 and path in group 2.
        # It excludes paths that already start with http:// or https://.
        markdown_content = re.sub(r"!\[(.*?)\]\((?!https?://)(.*?)\)", replace_image_link, markdown_content)

        # Ensure the output directory exists before writing
        ensure_dir(os.path.dirname(output_file_path))

        with codecs.open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

    except FileNotFoundError:
        print(f"Error: Input file not found during conversion: {input_file_path}", file=sys.stderr)
    except IOError as e:
        print(f"Error reading/writing file {input_file_path} or {output_file_path}: {e}", file=sys.stderr)
    except Exception as e:
        # Catch potential errors during html2text processing
        print(f"Error converting file {input_file_path}: {e}", file=sys.stderr)


def process_directory_recursive(input_root_dir, output_root_dir, converter):
    """
    Recursively processes a directory, converting all .html and .htm files
    to Markdown and replicating the directory structure.
    """
    print(f"Starting recursive processing of directory: {input_root_dir}")
    file_count = 0
    for root, dirs, files in os.walk(input_root_dir, topdown=True):
        # Calculate the relative path from the input root
        # This determines the structure within the output directory
        relative_path = os.path.relpath(root, input_root_dir)

        # Determine the corresponding output directory path
        # If relative_path is '.', it means we are at the root, output path is output_root_dir
        current_output_dir = os.path.join(output_root_dir, relative_path) if relative_path != '.' else output_root_dir

        # Removed directory creation from here.
        # ensure_dir will be called by convert_html_to_markdown only if a file needs saving.

        has_html_in_dir = False  # Flag to check if any HTML file exists in the current directory
        for file in files:
            if file.lower().endswith(('.html', '.htm')):
                has_html_in_dir = True  # Mark that an HTML file was found
                input_file_path = os.path.join(root, file)
                base, ext = os.path.splitext(file)
                output_filename = base + ".md"
                output_file_path = os.path.join(current_output_dir, output_filename)

                print(f"Converting: {input_file_path} -> {output_file_path}")
                convert_html_to_markdown(input_file_path, output_file_path, converter)
                file_count += 1

    print(f"Finished processing directory. Converted {file_count} files.")


def main():
    """Main function to parse arguments and initiate conversion."""
    parser = argparse.ArgumentParser(
        description="Convert HTML file(s) to Markdown. Creates an '{}' directory relative to the input path.".format(OUTPUT_DIR_NAME)
    )
    parser.add_argument("input_path", help="Path to the input HTML file or directory.")
    args = parser.parse_args()

    # Use absolute path for robustness
    input_path = os.path.abspath(args.input_path)
    # Output directory base path will be determined based on input type
    output_dir_base = None  # Initialize output_dir_base

    if not os.path.exists(input_path):
        print(f"Error: Input path not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Initialize the HTML to Markdown converter
    h = html2text.HTML2Text()
    # Set options for the converter if needed
    h.body_width = 0  # Disable automatic line wrapping for cleaner Markdown

    if os.path.isfile(input_path):
        if input_path.lower().endswith(('.html', '.htm')):
            # Handle single file input
            # Output directory is in the parent directory of the input file
            input_dir = os.path.dirname(input_path)
            output_dir_base = os.path.join(input_dir, OUTPUT_DIR_NAME)
            ensure_dir(output_dir_base)  # Create output dir
            print(f"Output will be saved in: {output_dir_base}")

            base_name = os.path.basename(input_path)
            name, ext = os.path.splitext(base_name)
            output_filename = name + ".md"
            # Place single converted file directly in the output base directory
            output_file_path = os.path.join(output_dir_base, output_filename)

            print(f"Converting single file: {input_path} -> {output_file_path}")
            convert_html_to_markdown(input_path, output_file_path, h)
            print("Conversion complete.")
        else:
            print(f"Error: Input file is not an HTML file (.html or .htm): {input_path}", file=sys.stderr)
            sys.exit(1)

    elif os.path.isdir(input_path):
        # Handle directory input
        # Output directory is inside the input directory
        output_dir_base = os.path.join(input_path, OUTPUT_DIR_NAME)
        ensure_dir(output_dir_base)  # Create output dir
        print(f"Output will be saved in: {output_dir_base}")

        process_directory_recursive(input_path, output_dir_base, h)
        # Completion message is printed inside process_directory_recursive

    else:
        # Handle cases where the path exists but is not a file or directory (e.g., socket, fifo)
        print(f"Error: Input path is not a valid file or directory: {input_path}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

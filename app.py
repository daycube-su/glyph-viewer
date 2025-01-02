from flask import Flask, request, render_template
from PIL import Image
from io import BytesIO
import base64
import os

app = Flask(__name__)


def create_markdown_table(glyph_data: dict) -> str:
    glyph = glyph_data["name"]
    name = glyph.split("_")[1]
    table = "| Unicode | Hex | Image |\n| --------- | --------- | --------- |\n"

    for row in glyph_data["data"]:
        char = f"\\u{name}{row['pos']}"
        let = bytes(char, "utf-8").decode("unicode-escape")
        img_data = f"data:image/png;base64,{row['img']}"
        table += f"| {let} | {char} | ![]({img_data}) |\n"

    return table


def resolve_glyphs(input_path: str):
    result = []

    if not os.path.exists(input_path):
        return result

    data = split_and_save_images(input_path)
    filename = os.path.splitext(os.path.basename(input_path))[0]
    result.append({"name": filename, "data": data})

    return result


def split_and_save_images(input_path: str):
    result = []

    with Image.open(input_path) as img:
        basename = os.path.basename(input_path)
        filename = basename.split(".")[0]
        glyph = filename.split("_")[1]

        width, height = img.size

        if width not in {128, 256, 2048} or height not in {128, 256, 2048}:
            return

        side_size = int(width / 128 * 8)

        for j in range(0, height, side_size):
            for i in range(0, width, side_size):
                box = (i, j, i + side_size, j + side_size)
                tile = img.crop(box)

                if is_empty_tile(tile):
                    continue

                x = j // side_size
                y = i // side_size
                path = to_hex(x) + to_hex(y)

                buffered = BytesIO()
                tile.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                result.append({"pos": path, "img": img_str})

    return result


def to_hex(value: int) -> str:
    return hex(value)[2:].upper()


def is_empty_tile(tile):
    pixel_data = list(tile.getdata())
    return all(pixel[3] == 0 for pixel in pixel_data)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file part"
    file = request.files["file"]
    if file.filename == "":
        return "No selected file"
    if file:
        filename = file.filename
        file_path = os.path.join("static", filename)
        file.save(file_path)

        data = resolve_glyphs(file_path)
        table = ""
        for glyph in data:
            table = create_markdown_table(glyph)

        os.remove(file_path)

        return render_template("index.html", table=table)


if __name__ == "__main__":
    app.run(debug=True)

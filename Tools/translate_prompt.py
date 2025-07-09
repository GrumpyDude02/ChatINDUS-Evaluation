from deep_translator import GoogleTranslator
import json, argparse, os

def translate_text(text, target_lang) -> str | Exception:
    try:
        return GoogleTranslator(target=target_lang).translate(text)
    except Exception as e:
        return e


def translate_json(file_path, output_file, target_lang, question_key:str = "prompt", save=True) -> dict:
    try:
        f = open(file_path)
        data: list = json.load(f)
        f.close()
    except (FileExistsError, FileNotFoundError):
        print("Invalid file path")
        return
    for i in range(len(data)):
        try:
            prompt = data[i][question_key]
            translation = translate_text(prompt, target_lang)
        except KeyError:
            print("Question key not found, check if the provided question key is correct (the default key that function uses is the \"prompt\")")
            return
        for _ in range(3):
            if not isinstance(translation, Exception):
                break
            translation = translate_text(prompt, target_lang)
    
        if not isinstance(translation, Exception):
            data[i][question_key] = translation
            data[i]["language"] = target_lang
        else:
            print(f"[Warning] Failed to translate prompt at index {i}")
    if save:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Translate the 'prompt' field in a JSON file to the specified language."
    )
    
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the input JSON file containing a list of objects with a 'prompt' field."
    )
    
    parser.add_argument(
        "language",
        type=str,
        help="Target language code for translation (e.g., 'fr' for French, 'es' for Spanish, 'de' for German)."
    )

    args = parser.parse_args()

    root = os.path.dirname(os.path.abspath(args.file_path))
    base, ext = os.path.splitext(args.file_path)
    output_file_with_lang = f"{base}_{args.language}{ext}"

    translate_json(args.file_path, output_file_with_lang, args.language)

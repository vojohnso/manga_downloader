from PIL import Image
from tqdm import tqdm
import cloudscraper
import os, sys, re, json, shutil


def main(manga_id, language):
    scraper = cloudscraper.create_scraper()
    try:
        request = scraper.get(f"https://mangadex.org/api/manga/{manga_id}")
        manga = json.loads(request.text)
    except (json.decoder.JSONDecodeError, ValueError):
        print("JSON Error With CloudFlare")
        exit(1)
    try:
        manga_title = manga["manga"]["title"]
    except:
        print("Not a Valid API endpoint. Enter a Mangadex manga, not chapter.")
    print(f"\nTitle: {manga_title}")
    collect_chapters(manga, scraper, language)


def collect_chapters(manga, scraper, lang_name):
    #grabbing all chapters that pertain to language
    chapters = {}
    chapter_num = []
    for chapter_id in manga["chapter"]:
        if manga["chapter"][chapter_id]["lang_name"] == lang_name:
            chapters[chapter_id] = manga["chapter"][chapter_id]
    if not chapters:
        print("There are no chapters to download.")
        exit(0)
    else:
        for chapter_id in chapters:
            if chapters[str(chapter_id)]['chapter'] not in chapter_num:
                chapter_num.append(chapters[str(chapter_id)]['chapter'])
        chapter_num.sort(key=float)
        print("Chapters: ")
        print(" " + ", ".join(chapter_num))

    #choosing the chapters to download, can either input one number "1",
    #multiple numbers such as "1, 2, 3" or a list of numbers "1-20"
    chap_req = input("Enter which chapter(s) to be downloaded: ").strip()
    if "-" not in chap_req:
        while True:
            if chap_req in chapter_num:
                break
            else:
                print(f"Chapter {chap_req} does not exist/cannot be found.")
                chap_req = input("Enter which chapter(s) to be downloaded: "). \
                    strip()
                chap_req.split()
                continue
    else:
        chap_req.strip()
        split = chap_req.split("-")
        all_chaps = list(range(int(split[0]), int(split[1]) + 1))
        while True:
            low_ch = all_chaps[0]
            high_ch = all_chaps[-1]
            try:
                low_ch_num = chapter_num.index(str(low_ch))
            except ValueError:
                print(f"Chapter {low_ch} does not exist/cannot be found. Skipping")
                all_chaps.remove(low_ch)
                continue
            try:
                high_ch_num = chapter_num.index(str(high_ch))
            except ValueError:
                print(f"Chapter {high_ch} does not exist/cannot be found. Skipping")
                all_chaps.remove(high_ch)
                continue
            chap_req = chapter_num[low_ch_num: high_ch_num + 1]
            break

    #isolating the chapters wanted to be downloaded
    chap_down = []
    for chap_id in chapters:
        chap_num = manga["chapter"][chap_id]["chapter"].replace(".0", "")
        group = manga["chapter"][chap_id]["group_name"]
        if group == "MangaPlus":
            #If group is MangaPlus, obtain chapter info from MangaPlus.
            pass
        for req_chap in chap_req:
            if int(chap_num) == int(req_chap): # and manga["chapter"][chapter]["lang_name"] == lang_name:
                        chap_down.append((str(chap_num), chap_id, group))
        chap_down.sort(key=lambda x: float(x[0]))

    #obtaining the pages
    print()
    manga_title = manga["manga"]["title"]
    revised_title = rename_chapter(manga_title)
    save_path = os.path.join(download_folder, revised_title)
    for item in chap_down:
        print(f"Downloading Chapter {item[0]}.")
        request = scraper.get(f"https://mangadex.org/api/chapter/{item[1]}/")
        chapter = json.loads(request.text)
        chapter_folder = os.path.join(save_path, "Chapter " + item[0] + " " +
                                      item[2])
        if not os.path.exists(chapter_folder):
            os.makedirs(chapter_folder)
        image_list = []
        hashcode = chapter["hash"]
        server = chapter["server"]
        for page in chapter["page_array"]:
            image_list.append(f"{server}{hashcode}/{page}")

    #downloading the chapters
        for num, img in tqdm(enumerate(image_list, 1)):
            page_file = os.path.join(chapter_folder, str(num))
            picture = scraper.get(img)
            with open(f"{page_file}", 'wb') as f:
                f.write(picture.content)
    #pdf things
        delete_pdf(chapter_folder)
        convert_to_pdf(chapter_folder)


def convert_to_pdf(chapter_folder):
    # converts all of the images in the current chapter directory into a pdf
    first = True
    page_1 = None
    os.chdir(chapter_folder)
    image_list = []
    for i in sorted(os.listdir(chapter_folder), key=len):
        with Image.open(i) as image:
            im = image.convert('RGB')
            if first:
                page_1 = im
                first = False
            else:
                image_list.append(im)
        page_1.save(f"{chapter_folder}.pdf",
                    resolution=100.0, save_all=True, append_images=image_list)
    # must delete the folder with all the individual images
    try:
        os.chdir("../")
        shutil.rmtree(os.path.relpath(chapter_folder))
        print('Deleting obsolete folder.')
    except FileNotFoundError:
        print("The file does not exist? This is confounding!")


def delete_pdf(chapter_folder):
# if the pdf already exists, prompts the user to delete or not
    if os.path.isfile(f"{chapter_folder}.pdf"):
        while True:
            prompt = input('The PDF already exists. Enter "Y" to delete and'
                           'replace, or enter "N" to continue')
            if prompt.upper() == "Y":
                os.remove(f"{chapter_folder}.pdf")
                break
            elif prompt.upper() == "N":
                break


def rename_chapter(manga_title):
    # if the manga has a character in its title that is unusable, rename it
    bad_chars = ['\\', '/', ':', '*', '?', "<", ">", "|"]
    for char in bad_chars:
        if char in manga_title:
            manga_title = manga_title.replace(char, "")
    return manga_title


if __name__ == "__main__":
    if len(sys.argv) == 2:
        lang_name = sys.argv[1]
    else:
        lang_name = "English"
    url = input("Enter Manga URL: ")
    try:
        if "mangadex.org" in url:
            manga_id = re.search("\\d+", url).group()
    except:
        print("This is not a proper mangadex URL.")
    print()
    while True:
        try:
            download_folder = input("Download Folder: ")
            os.chdir(download_folder)
            break
        except FileNotFoundError:
            print("Cannot Find Such Folder. Try Again.")
    main(manga_id, lang_name)


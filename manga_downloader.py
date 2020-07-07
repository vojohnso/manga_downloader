from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from PIL import Image
from tqdm import tqdm
import re
import shutil
import requests
import os

options = Options()
Options.headless = True
url = 'https://kissmanga.com/'
save_path = r"save_path"
PATH = r"chromedriver_path"


class Download:
    def __init__(self):
        self.browser = webdriver.Chrome(options=options, executable_path=PATH)
        self.chapters = []
        self.chapters_list = {}
        self.search_options = {}
        self.manga_title = ""
        self.num = 1
        self.low_ch = 1
        self.high_ch = 1
        self.current_link = ""
        self.start()

    def start(self):
        while True:
            try:
                self.browser.get(url)
                WebDriverWait(self.browser, 10).until(
                    EC.presence_of_element_located((By.ID, "keyword"))
                )
                self.search()
                break
            except TimeoutException:
                print("Please check the url or your internet connection."
                      "\nPlease retry.")
        self.get_chapters()
        self.end()

    def search(self):
        # used to search for a title by user input
        element = self.browser.find_element_by_id("keyword")
        search = input("What title are you looking for? Please be specific.")
        element.send_keys(search, Keys.RETURN)
        # if this is true, continue, else skip to get_chapters()
        if not self.check_search():
            self.get_chapters()
            self.end()
        try:
            table = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            manga_title = table.find_elements_by_tag_name("tr")
            for i in range(2, len(manga_title)):
                choice = manga_title[i].find_element_by_tag_name("td")
                print(f"{i - 1}. {choice.text}")
                self.search_options[str(i - 1)] = choice.text.strip()
            user_choice = input("\nInput the number that correspond to the "
                                "correct title, or input '*' to go back.")
            if user_choice == "*":
                self.browser.back()
                self.search()
            while True:
                if user_choice in self.search_options.keys():
                    link = self.browser.find_element_by_link_text(
                        self.search_options[user_choice])
                    link.click()
                    break
                else:
                    user_choice = input("\nPlease input a proper number, or"
                                        " input '*' to go back.")
        except NameError:
            print("Sorry we couldn't find any titles related to your input.\n"
                  "Please be more specific.")
            self.end()

    def get_chapters(self):
        # creates a list of all the chapters wanted
        self.current_link = self.browser.current_url
        title = self.browser.find_element_by_class_name("bigChar")
        self.manga_title = title.text
        list_of_chapters = []
        print(f"\nGetting chapters from {self.manga_title}...\nPlease Wait...")
        try:
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            list_of_chapters = self.browser.find_elements_by_xpath(
                "//tbody/tr/td/a")
            # reversing the chapters to start from beginning
            list_of_chapters = list_of_chapters[::-1]
            for chapter in list_of_chapters:
                self.chapters_list[find_chapter_number(chapter)] = \
                    chapter.get_attribute("href")
        except TimeoutException:
            print("Couldn't find the chapters! Check your internet connection!")
            self.start()
        print('\nChoose which chapters to print from:')
        self.low_ch = int(input("Starting Chapter:"))
        self.high_ch = int(input("Ending Chapter:"))
        self.num = self.low_ch
        self.rename_chapter()
        try:
            os.mkdir(f"{save_path}\\{self.manga_title}")
            print('Making directory...')
        except FileExistsError:
            print(f"\n{self.manga_title} directory already exists...")
        os.chdir(save_path)
        for chapter in self.chapters_list:
            if self.low_ch <= chapter <= self.high_ch:
                self.chapters.append([chapter, self.chapters_list[chapter]])
        # self.chapters = self.chapters[self.low_ch - 1:self.high_ch]
        for ch in self.chapters:
            self.num = ch[0]
            self.download_chapter(ch[1])
            self.convert_to_pdf()
            # self.num += 1
        print("\nDone!")

    def download_chapter(self, chapter_link):
        # downloads each individual chapter
        img_list = []
        num = 1
        try:
            os.mkdir(
                f"{save_path}\\{self.manga_title}\\Chapter {self.num}")
            print(f"\nCreating Chapter {self.num} folder.")
        except FileExistsError:
            pass
        self.browser.get(chapter_link)
        self.if_capcha()
        try:
            WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'a'))
            )
        except TimeoutException:
            print("\nCouldn't load the page! Check your internet connection!")
        for img in tqdm(
                self.browser.find_elements_by_xpath('//div[@id="divImage'
                                                    '"]/p/img')):
            img_list.append(img)
            url = img.get_attribute("src")
            end = url.split(".")[-1]
            picture = requests.get(url)
            with open(f"{save_path}\\{self.manga_title}\\Chapter {self.num}\\"
                      f"Page {num}.{end}", 'wb') as f:
                f.write(picture.content)
                num += 1
        self.browser.get(self.current_link)
        self.delete_pdf()

    def convert_to_pdf(self):
        # converts all of the images in the current chapter directory into a pdf
        print(f"Creating pdf of chapter {self.num}.")
        first = True
        page_1 = None
        os.chdir(f"{save_path}\\{self.manga_title}\\Chapter {self.num}")
        image_list = []
        for i in sorted(os.listdir(f"{save_path}\\{self.manga_title}\\Chapter "
                                   f"{self.num}"), key=len):

            image = Image.open(i)
            im = image.convert('RGB')
            if first:
                page_1 = im
                first = False
            else:
                image_list.append(im)
        page_1.save(f"{save_path}\\{self.manga_title}\\Chapter {self.num}.pdf",
                    resolution=100.0, save_all=True, append_images=image_list)
        # must delete the folder with all the individual images
        try:
            os.chdir("../")
            shutil.rmtree(f"Chapter {self.num}")
            print('Deleting obsolete folder.')
        except FileNotFoundError:
            print("The file does not exist? This is confounding!")

    def rename_chapter(self):
        # if the manga has a character in its title that is unusable, rename it
        bad_chars = ['\\', '/', ':', '*', '?', "<", ">", "|"]
        for char in bad_chars:
            if char in self.manga_title:
                self.manga_title = self.manga_title.replace(char, "")

    def if_capcha(self):
        # checks if a capcha pops up
        try:
            WebDriverWait(self.browser, 3).until(EC.presence_of_element_located
                                                 ((By.XPATH,
                                                   '/html/body/div/div/div'
                                                   '/div/form/div'))
                                                 )
            input("\nIf prompted with a capcha, please complete it and"
                  " press enter. ")
        except:
            pass

    def check_search(self):
        # checks to see if search options automatically opened manga page or not
        return self.browser.current_url == "https://kissmanga.com/Search/Manga"

    def delete_pdf(self):
        # if the pdf already exists, prompts the user to delete or not
        if os.path.isfile(f"{save_path}\\{self.manga_title}\\"
                          f"Chapter {self.num}.pdf"):
            while True:
                prompt = input("This pdf already exists? Input 'y' if you want "
                               "to replace it, or 'n' to keep it:")
                if prompt.upper() == "Y":
                    os.remove(f"{save_path}\\{self.manga_title}\\"
                              f"Chapter {self.num}.pdf")
                    break
                elif prompt.upper() == "N":
                    break

    def end(self):
        # prompts the user when the program ends
        while True:
            next_step = input("What would you like to do next? Input 'GO' to "
                              "download another title, and input 'EXIT' to "
                              "exit.")
            if next_step.upper() == 'EXIT':
                self.exit()
                break
            elif next_step.upper() == 'GO':
                self.browser.quit()
                Download()

    def exit(self):
        # exits the program
        print('Exiting:')
        self.browser.quit()


def find_chapter_number(chapter):
    text = chapter.text
    chapterRegex = re.compile(r"\d+\.?\d*")

    if "vol." in text.lower():
        sep = re.compile(r" Vol\. \d+")
        text = sep.sub("", text)
    number = chapterRegex.search(text)
    result = number.group()
    if "." in result:
        return float(result)
    else:
        return int(result)


if __name__ == "__main__":
    Download()

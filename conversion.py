from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.common.exceptions import NoAlertPresentException

import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    """
    Replace ISBN with ISBN13 in books table using browser automation and online converter
    """

    # Initialize counter
    counter = 0

    # Initialize list to track bad ISBN
    bad = []

    # Set chromedriver to brower variable
    browser = webdriver.Chrome('/mnt/c/selenium/chromedriver.exe')

    # Open web page
    browser.get('https://www.isbn.org/ISBN_converter')

    # Set form to input box
    form = browser.find_element_by_id('edit-isbn10')

    # Open CSV file and set to reader
    f = open("books.csv")
    reader = csv.reader(f)

    # Iterate over file
    for isbn, title, author, year in reader:

        book = db.execute("SELECT * FROM books WHERE isbn = :isbn AND isbn13 IS NOT NULL", {"isbn": isbn}).fetchone()

        if book:

            print(f'already in db. {book.isbn}')

        else:

            try:

                # Enter ISBN into online form
                form.send_keys(isbn)
                form.send_keys(Keys.ENTER)

                # Only execute on first iteration
                if not counter:

                    while True:

                        # Wait for response
                        if browser.find_element_by_id('isbn13_conversion').text and not counter:

                            # Assign response to isbn13 and break loop
                            isbn13 = browser.find_element_by_id('isbn13_conversion').text
                            break
                
                # For all subsequent iterations
                else:

                    # Loop until conversion updates and assign new value to isbn13
                    while True:
                        if browser.find_element_by_id('isbn13_conversion').text != isbn13:
                            print(f'{browser.find_element_by_id("isbn13_conversion").text}, {isbn13}')
                            isbn13 = browser.find_element_by_id('isbn13_conversion').text
                            break

                # Strip '-' from isbn13
                isbn13_stripped = ''.join([char for char in isbn13 if char != '-'])

                # If 'Bad ISBN' according to isbn.org
                if 'Bad' in isbn13_stripped:

                    # Slap a 978 on the front and to the list
                    isbn13_stripped = '978' + isbn13_stripped[-10:]
                    bad.append(isbn)


                # Add isbn13 to books table
                db.execute("UPDATE books SET isbn13 = :isbn13 WHERE isbn = :isbn", {"isbn13": isbn13_stripped, "isbn": isbn})
                db.commit()

                print(f"{counter}, {isbn13_stripped}")

            except UnexpectedAlertPresentException:

                try:
                    print('ALERT!')
                    alert = browser.switch_to.alert()
                    alert.accept()

                except NoAlertPresentException:
                    print('No Alert')

                finally:
                    bad.append(isbn)

            finally:

                # Clear the form
                form.clear()

                # Increment counter
                counter += 1
        
    with open('bad.csv', 'w') as F:
        writer = csv.writer(F)
        for isbn in bad:
            writer.writerow(isbn)

if __name__ == "__main__":
    main()




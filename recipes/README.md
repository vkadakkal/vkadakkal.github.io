# Nammade Recipes

Static HTML/CSS/JavaScript cookbook served by GitHub Pages at /recipes/.

Data: https://sheetdb.io/api/v1/f8419edfrw92n, tab recipes.
Columns: id, title, ingredients, method, notes, source_url, status, updated_at.
Ingredients and method use one item/step per line. IDs must be unique and consist of letters, digits, and hyphens. Drafts can omit ingredients or method.

READ, CREATE and UPDATE permissions and browser CORS must be enabled in SheetDB. This public browser app uses the supplied public endpoint; visitors with access to it can read and edit recipes. Do not store private data or put credentials in the static page. Private editing would require an authenticated backend.

Source import: 14 entries from https://sites.google.com/view/mmrecipe/home. Avial, Baby Potato Masala and Hyderabadi Biriyani are drafts because the original pages are unfinished. All original ingredient quantities and directions are preserved; missing information has not been invented.

Run locally: python -m http.server 8765
Open http://localhost:8765/.
No build step or third-party JavaScript dependencies.

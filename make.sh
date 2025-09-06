# 1) create a virtualenv (optional but recommended)
python3 -m venv .venv
# mac/linux:
source .venv/bin/activate
# windows:
# .venv\Scripts\activate

# 2) install deps
pip3 install -r requirements.txt

# 3) place these two files next to the script:
#    - your preprint PDF
#    - the cover image (jpg/png or pdf)


python3 src/build_book.py \
  --index-pdf "index.pdf" \
  --cover "cover.jpeg" \
  --out "output/Agentic_Design_Patterns_compiled.pdf" \
  --workdir "_agentic_build" \
  --add-toc
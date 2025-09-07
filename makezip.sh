mkdir -p dist
ZIP=$(realpath dist/vocal_vse.zip)

rm -fv $ZIP
zip -9 -r "$ZIP" vocal_vse -i '*.py'
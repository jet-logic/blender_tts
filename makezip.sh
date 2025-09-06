# python << EOF
# from vocal_vse import bl_info
# print(bl_info["version"])
# EOF
mkdir -p dist
ZIP=$(realpath dist/vocal_vse.zip)

rm -fv $ZIP
zip -9 -r "$ZIP" vocal_vse -i '*.py'
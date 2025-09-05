# python << EOF
# from tts_narration import bl_info
# print(bl_info["version"])
# EOF
mkdir -p dist
ZIP=$(realpath dist/tts_narration.zip)

rm -fv $ZIP
zip -r "$ZIP" tts_narration -i '*.py'
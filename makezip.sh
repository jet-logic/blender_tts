# python << EOF
# from tts_narration import bl_info
# print(bl_info["version"])
# EOF

ZIP=$(realpath dist/tts_narration.zip)
mkdir -p dist
rm -fv $ZIP
zip -r $ZIP tts_narration -i '*.py'
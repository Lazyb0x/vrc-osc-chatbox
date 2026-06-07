#!/bin/bash

# 下载并构建词库文件到 public/rime 目录

# 雾凇拼音
curl -L -o /tmp/cn_dicts.zip https://github.com/iDvel/rime-ice/releases/latest/download/cn_dicts.zip
unzip -o /tmp/cn_dicts.zip -d ./rime-ice-cn-dicts/
find ./rime-ice-cn-dicts -name '*.dict.yaml' -exec mv {} ./ \;
rm -rf ./rime-ice-cn-dicts/

# 萌娘百科
curl -L -o ./moegirl.dict.yaml https://github.com/outloudvi/mw2fcitx/releases/latest/download/moegirl.dict.yaml

docker build --target base -t rime-base .
docker build -t rime-builder .
docker create --name rime-build rime-builder
docker cp rime-build:/rime_user/build/ ./build
docker rm -f rime-build
docker rmi rime-builder

cp ./build/luna_pinyin.custom.*.bin ../public/rime/
sed -i 's/^\(  dictionary: \).*/\1luna_pinyin.custom/' ../public/rime/luna_pinyin.schema.yaml

rm -rf ./build
find . -maxdepth 1 -name '*.dict.yaml' ! -name 'luna_pinyin.custom.*.yaml' -delete

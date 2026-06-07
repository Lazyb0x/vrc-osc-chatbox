FROM ubuntu:26.04 as base

RUN apt-get update && apt-get install -y \
    librime-bin \
    librime-data \
    rime-data-luna-pinyin \
    rime-essay \
    rime-prelude \
    && rm -rf /var/lib/apt/lists/*

FROM base AS build

COPY . /rime_user/
WORKDIR /rime_user

RUN mkdir -p build && \
    rime_deployer --build /rime_user /usr/share/rime-data /rime_user/build

CMD ["bash"]
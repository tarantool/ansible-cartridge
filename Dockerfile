# Package builders
FROM centos:7 AS packages-builder

RUN set -x \
    && curl -sL https://rpm.nodesource.com/setup_8.x | bash - \
    && yum -y install nodejs git gcc make cmake unzip

RUN git config --global user.email "test@tarantool.io" \
    && git config --global user.name "Tar Antool"

# Enterprise
FROM packages-builder AS enterprise-packages-builder

ARG TARANTOOL_DOWNLOAD_TOKEN
ARG BUNDLE_VERSION

RUN curl -O -L https://tarantool:${TARANTOOL_DOWNLOAD_TOKEN}@download.tarantool.io/enterprise/tarantool-enterprise-bundle-${BUNDLE_VERSION}.tar.gz \
    && tar -xzf tarantool-enterprise-bundle-${BUNDLE_VERSION}.tar.gz \
    && rm -rf tarantool-enterprise-bundle-${BUNDLE_VERSION}.tar.gz

ENV PATH="/tarantool-enterprise:${PATH}"

RUN tarantoolctl rocks install cartridge-cli \
    &&  .rocks/bin/cartridge create --name myapp . \
    && sed -i 's/cartridge == 1.0.0-1/cartridge == 1.2.0/g' myapp/myapp-scm-1.rockspec \
    && .rocks/bin/cartridge pack rpm --version 1.0.0 myapp \
    && .rocks/bin/cartridge pack deb --version 1.0.0 myapp

RUN mkdir /opt/myapp && cp myapp-1.0.0-0.rpm myapp-1.0.0-0.deb /opt/myapp/


# Opensource 1.10
FROM packages-builder AS opensource-1.10-packages-builder

RUN curl -s https://packagecloud.io/install/repositories/tarantool/1_10/script.rpm.sh | bash
RUN yum install -y tarantool tarantool-devel

ENV PATH=$PWD:$PATH

RUN tarantoolctl rocks install cartridge-cli \
    &&  .rocks/bin/cartridge create --name myapp . \
    && sed -i 's/cartridge == 1.0.0-1/cartridge == 1.2.0/g' myapp/myapp-scm-1.rockspec \
    && .rocks/bin/cartridge pack rpm --version 1.0.0 myapp \
    && .rocks/bin/cartridge pack deb --version 1.0.0 myapp

RUN mkdir /opt/myapp && cp myapp-1.0.0-0.rpm myapp-1.0.0-0.deb /opt/myapp/


# Opensource 2.2
FROM packages-builder AS opensource-2.2-packages-builder

RUN curl -s https://packagecloud.io/install/repositories/tarantool/2_2/script.rpm.sh | bash
RUN yum install -y tarantool tarantool-devel

ENV PATH=$PWD:$PATH

RUN tarantoolctl rocks install cartridge-cli \
    &&  .rocks/bin/cartridge create --name myapp . \
    && sed -i 's/cartridge == 1.0.0-1/cartridge == 1.2.0/g' myapp/myapp-scm-1.rockspec \
    && .rocks/bin/cartridge pack rpm --version 1.0.0 myapp \
    && .rocks/bin/cartridge pack deb --version 1.0.0 myapp

RUN mkdir /opt/myapp && cp myapp-1.0.0-0.rpm myapp-1.0.0-0.deb /opt/myapp/


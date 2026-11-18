# SPDX-License-Identifier: GPL-3.0-or-later
# Kleinia installer (ReadyMade fork) — build entry.
# build/test/package follow the org-wide unified interface; `artifact`
# builds the RPM-carrier OCI image consumed by the kleinia assembly repo
# (artifacts.yml); `push` publishes it ($KLN_REGISTRY contract).
# Clone with --recurse-submodules (crates/taidan_proc_macros).

version := `git describe --tags --always 2>/dev/null || echo 0.1.0`

default: build

build:
    cargo build --release
    mkdir -p build-out
    cp target/release/readymade build-out/
    # libhelium-1 is the one C dependency missing from Fedora repos:
    # bundle the runtime .so next to the binary so nfpm ships both
    cp -L /usr/lib64/libhelium-1.so.1 build-out/

test:
    test -x build-out/readymade
    test $(stat -c %s build-out/readymade) -gt 1000000
    ! ldd build-out/readymade | grep -q "not found"

package: build
    sed "s/{{"{{PKG_VERSION}}"}}/{{version}}/" dist/nfpm.yaml > .nfpm.rendered.yaml
    nfpm pkg -f .nfpm.rendered.yaml -p rpm -t build-out/
    rm -f .nfpm.rendered.yaml

image:
    podman build -f dist/Containerfile -t localhost/kleinia/kleinia-installer:{{version}} .

artifact:
    podman build -f dist/Containerfile --target artifacts -t localhost/kleinia/kleinia-installer:rpm .

push:
    bash scripts/push.sh

clean:
    rm -rf build-out target .nfpm.rendered.yaml

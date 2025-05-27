{ pkgs }: {
  deps = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.openssl
    pkgs.libffi
    pkgs.pkg-config
    pkgs.cacert
  ];
}

{ pkgs ? import <nixpkgs> {} }:
let
  my-python-packages = python-packages: [
    python-packages.pip
    python-packages.setuptools
  ];
  my-python = pkgs.python38.withPackages my-python-packages;
in
  pkgs.mkShell {
    buildInputs = with pkgs; [
      my-python
    ];
    shellHook = ''
      export PIP_PREFIX="/home/david/dev/spisbot/_build/pip_packages"
      export PYTHONPATH="/home/david/dev/spisbot/_build/pip_packages/lib/python3.8/site-packages:$PYTHONPATH" 
      unset SOURCE_DATE_EPOCH
    '';
  }

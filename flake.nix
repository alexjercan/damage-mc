{
  description = "A basic flake for my Projects";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
  }: (
    flake-utils.lib.eachDefaultSystem
    (system: let
      pkgs = import nixpkgs {
        inherit system;

        config = {
          allowUnfree = true;
        };
      };
    in {
      packages = {
          default = {}; # TODO: Add package here
      };

      apps = {
        # TODO: Add app here
        # default = flake-utils.lib.mkApp {
        #   drv = ...;
        # };
      };

      devShells.default = pkgs.mkShell rec {
        nativeBuildInputs = [];

        buildInputs = with pkgs; [
          flite
          glfw
          gradle
          jdk21
          libGL
          openal
          alsa-lib

          pkgsCross.avr.buildPackages.gcc
          pkgsCross.avr.buildPackages.avrdude
        ];

        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath buildInputs;

        shellHook = ''
          export JAVA_HOME=${pkgs.jdk21}
        '';
      };
    })
  );
}

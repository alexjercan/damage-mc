{
  description = "Development environment for DamageIO game integrations and Arduino firmware";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs @ { flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];

      perSystem = { system, ... }: let
        pkgs = import inputs.nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in {
        devShells.default = pkgs.mkShell rec {
          buildInputs = with pkgs; [
            flite
            glfw
            gradle
            jdk21
            (python3.withPackages (ps: [ ps.pyserial ps.mss ps.pillow ]))
            tesseract
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
      };
    };
}

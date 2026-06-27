{
  description = "The Grace Space - Django portfolio site";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, flake-utils, nixpkgs }: flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = import nixpkgs { inherit system; };
    in
    {
      devShell = pkgs.mkShell {
        # Toolchain only. Python packages live in requirements.txt and are
        # installed into a .venv by direnv (`layout python`). Adding a Python
        # dep does NOT require touching this file or reloading direnv.
        buildInputs = [
          pkgs.python312
          pkgs.postgresql_18
          pkgs.tailwindcss   # standalone Tailwind CLI, no npm/node_modules
          pkgs.uv
        ];
      };
    });
}

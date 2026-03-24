{
  origInputs,
  pkgs,
  lib,
  ...
}:

rec {
  workspace = origInputs.uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ../.; };

  overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

  zbarOverlay = final: prev: {
    pyzbar = prev.pyzbar.overrideAttrs (old: {
      buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.zbar ];

      postInstall = (old.postInstall or "") + ''
        substituteInPlace $out/${pkgs.python3.sitePackages}/pyzbar/zbar_library.py \
          --replace-fail "find_library('zbar')" '"${lib.getLib pkgs.zbar}/lib/libzbar${pkgs.stdenv.hostPlatform.extensions.sharedLibrary}"'
      '';
    });
  };

  pythonSet =
    (pkgs.callPackage origInputs.pyproject-nix.build.packages {
      python = pkgs.python3;
    }).overrideScope
      (
        lib.composeManyExtensions [
          origInputs.pyproject-build-systems.overlays.wheel
          overlay
          zbarOverlay
        ]
      );

  packageSet = pythonSet.overrideScope (
    final: prev: {
      backend = prev.backend.overrideAttrs (old: {
        src = lib.fileset.toSource rec {
          root = ../.;

          fileset = lib.fileset.unions [
            (root + "/pyproject.toml")
            (root + "/packages/backend")
          ];
        };
      });
    }
  );
}

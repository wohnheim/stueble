{
  origInputs,
  pkgs,
  ...
}:

let
  common = pkgs.callPackage ./python-common.nix { inherit origInputs; };
in
{
  # Backend production package
  packages.backend = common.packageSet.mkVirtualEnv "backend-env" common.workspace.deps.default;
}

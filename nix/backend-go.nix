{
  lib, 
  pkgs,
  ...
}:

{
  packages.backendGo = pkgs.buildGoModule {
    pname = "backend-go";
    version = "0.1";

    src = ../packages/backend-go;

    vendorHash = "sha256-sN2ZTy2XcQ1M/39+T6iKwRuJmf3MCPG+h4qu/fdTVbc=";
  };
}

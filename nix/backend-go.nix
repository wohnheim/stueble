{
  lib, 
  pkgs,
  ...
}:

{
  packages.backendGo = pkgs.buildGoModule {
    pname = "backend-go";
    version = "0.1";

    src = ../packages/login;

    vendorHash = "sha256-KloM9UlIzup855HHvCc9EQzCZkDDTJCGPHkBmJsRFho=";
  };
}

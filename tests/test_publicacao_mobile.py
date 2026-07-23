import json
import struct
import xml.etree.ElementTree as ET
from pathlib import Path


RAIZ = Path(__file__).parents[1]
MOBILE = RAIZ / "mobile"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"


def _dimensoes_png(caminho: Path) -> tuple[int, int]:
    dados = caminho.read_bytes()
    assert dados[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", dados[16:24])


def test_manifesto_web_tem_identidade_instalavel() -> None:
    manifesto = json.loads(
        (MOBILE / "web" / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifesto["name"] == "Mapa de Karnaugh Estendido"
    assert manifesto["display"] == "standalone"
    assert manifesto["theme_color"] == "#7A1024"
    assert manifesto["lang"] == "pt-BR"

    icones = {
        item["src"]: item
        for item in manifesto["icons"]
    }
    assert icones["icons/Icon-192.png"]["sizes"] == "192x192"
    assert icones["icons/Icon-512.png"]["sizes"] == "512x512"
    assert icones["icons/Icon-maskable-512.png"]["purpose"] == "maskable"

    assert _dimensoes_png(MOBILE / "web" / "icons" / "Icon-192.png") == (
        192,
        192,
    )
    assert _dimensoes_png(MOBILE / "web" / "icons" / "Icon-512.png") == (
        512,
        512,
    )


def test_android_tem_internet_nome_e_icones_adaptativos() -> None:
    raiz = ET.parse(
        MOBILE / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    ).getroot()
    permissoes = {
        elemento.attrib[f"{ANDROID_NS}name"]
        for elemento in raiz.findall("uses-permission")
    }
    aplicativo = raiz.find("application")

    assert "android.permission.INTERNET" in permissoes
    assert aplicativo is not None
    assert aplicativo.attrib[f"{ANDROID_NS}label"] == "Mapa de Karnaugh"
    assert aplicativo.attrib[f"{ANDROID_NS}roundIcon"] == (
        "@mipmap/ic_launcher_round"
    )
    assert (
        MOBILE
        / "android"
        / "app"
        / "src"
        / "main"
        / "res"
        / "mipmap-anydpi-v26"
        / "ic_launcher.xml"
    ).exists()


def test_release_android_usa_chave_propria() -> None:
    gradle = (
        MOBILE / "android" / "app" / "build.gradle.kts"
    ).read_text(encoding="utf-8")
    exemplo = (
        MOBILE / "android" / "key.properties.example"
    ).read_text(encoding="utf-8")
    gitignore = (
        MOBILE / "android" / ".gitignore"
    ).read_text(encoding="utf-8")

    assert 'rootProject.file("key.properties")' in gradle
    assert 'signingConfigs.getByName("release")' in gradle
    assert 'signingConfigs.getByName("debug")' not in gradle
    assert "keyAlias=mapa-karnaugh" in exemplo
    assert "key.properties" in gitignore
    assert "**/*.jks" in gitignore

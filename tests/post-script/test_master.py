import ProdPostInstall
import pytest

def test_install_utils():
    assert ProdPostInstall.install_utils() == 0

def test_install_docker():
    assert ProdPostInstall.install_docker() == 0

def test_ldap_cert_create():
    assert ProdPostInstall.generate_ldap_ssl_cert() == 0

def test_install_glauth():
    assert ProdPostInstall.install_glauth() == 0

def test_install_ldap():
    assert ProdPostInstall.install_ldap_client() == 0

def test_install_goofys():
    assert ProdPostInstall.install_goofys("hfjdskfhdjskhdj", "fjdkjfhdskfbhj", "bucket") == 0

def test_update_bashrc():
    assert ProdPostInstall.update_bashrc() == 0


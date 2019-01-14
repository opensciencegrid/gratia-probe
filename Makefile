PYTHON_ROOT_FILES := common/gratia/__init__.py
PYTHON_COMMON_FILES := common/gratia/common/*.py
PYTHON_COMMON2_FILES :=  common2/gratia/common2/*.py

INSTALL_PYTHON_DIR := $(shell python -c 'from distutils.sysconfig import get_python_lib; print get_python_lib()')

_default: install_python

install_python:
	mkdir -p $(DESTDIR)/$(INSTALL_PYTHON_DIR)/gratia/common
	mkdir $(DESTDIR)/$(INSTALL_PYTHON_DIR)/gratia/common2
	install -p -m 0644 $(PYTHON_ROOT_FILES) $(DESTDIR)/$(INSTALL_PYTHON_DIR)/gratia/
	install -p -m 0644 $(PYTHON_COMMON_FILES) $(DESTDIR)/$(INSTALL_PYTHON_DIR)/gratia/common/
	install -p -m 0644 $(PYTHON_COMMON_FILES) $(DESTDIR)/$(INSTALL_PYTHON_DIR)/gratia/common2/

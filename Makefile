# Inphic Control 通用安装规则（供 RPM / DEB / Arch / Flatpak 等打包共用）
#
#   make install DESTDIR=/tmp/pkg PREFIX=/usr
#   make uninstall DESTDIR=/tmp/pkg PREFIX=/usr
#   make print-version
#
# Flatpak 等使用 /app 前缀: make install PREFIX=/app INSTALL_UDEV=0

NAME         := inphic-control
VERSION      := $(shell sed -n 's/^__version__ = "\(.*\)"/\1/p' inphic_control/__init__.py)
PREFIX       ?= /usr
DESTDIR      ?=
INSTALL_UDEV ?= 1

DATADIR  = $(DESTDIR)$(PREFIX)/share
BINDIR   = $(DESTDIR)$(PREFIX)/bin
APPDIR   = $(DATADIR)/applications
ICONDIR  = $(DATADIR)/icons/hicolor/scalable/apps
UDEVDIR  = $(DESTDIR)$(PREFIX)/lib/udev/rules.d

.PHONY: all install uninstall print-version

all:
	@echo "inphic-control $(VERSION): 纯 Python, 无需编译。"
	@echo "安装: make install DESTDIR=<目录> [PREFIX=/usr] [INSTALL_UDEV=0]"

print-version:
	@echo $(VERSION)

install:
	install -Dpm 0755 packaging/$(NAME) $(BINDIR)/$(NAME)
	rm -rf $(DATADIR)/$(NAME)
	install -d $(DATADIR)/$(NAME)
	cp -r inphic_control $(DATADIR)/$(NAME)/
	find $(DATADIR)/$(NAME) -type d -name '__pycache__' -prune -exec rm -rf {} +
	find $(DATADIR)/$(NAME) -name '*.pyc' -delete
	install -Dpm 0644 packaging/$(NAME).desktop $(APPDIR)/$(NAME).desktop
	install -Dpm 0644 packaging/$(NAME).svg $(ICONDIR)/$(NAME).svg
ifeq ($(INSTALL_UDEV),1)
	install -Dpm 0644 packaging/70-inphic-in6.rules $(UDEVDIR)/70-inphic-in6.rules
endif

uninstall:
	rm -f $(BINDIR)/$(NAME)
	rm -rf $(DATADIR)/$(NAME)
	rm -f $(APPDIR)/$(NAME).desktop
	rm -f $(ICONDIR)/$(NAME).svg
ifeq ($(INSTALL_UDEV),1)
	rm -f $(UDEVDIR)/70-inphic-in6.rules
endif

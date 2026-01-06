# PyRpiCamController Release Workflow

Complete guide for version management, testing, and distribution of PyRpiCamController.

## 🔄 **Git Workflow**

### **Branch Strategy**
```
main (protected, releases only)
├── v1.0.0 (tag)  
├── v1.1.0 (tag)
└── v1.2.0 (tag)

dev (development, testing)
├── feature/camera-improvements
├── feature/web-ui-updates
└── bugfix/smb-permissions

feature branches
├── Merge to dev first
├── Test in dev
└── PR to main (triggers release)
```

### **Setup Git Workflow**
```bash
# Initial setup
git checkout -b dev
git push -u origin dev

# Feature development
git checkout dev
git checkout -b feature/new-feature
# ... make changes ...
git add .
git commit -m "Add new feature"
git push origin feature/new-feature

# Merge to dev for testing
git checkout dev  
git merge feature/new-feature
git push origin dev

# After testing, merge to main for release
git checkout main
git merge dev
git push origin main  # This triggers release process
```

---

## 📋 **Release Management Commands**

### **Development Testing**
```bash
# Test current code without releasing
python3 tools/release_manager.py test
```

### **Prepare New Release**
```bash
# Patch release (bug fixes): 1.0.0 → 1.0.1
python3 tools/release_manager.py prepare patch

# Minor release (new features): 1.0.0 → 1.1.0  
python3 tools/release_manager.py prepare minor

# Major release (breaking changes): 1.0.0 → 2.0.0
python3 tools/release_manager.py prepare major
```

### **Build Release Package**
```bash
# Build distribution zip after prepare
python3 tools/release_manager.py build
```

### **Complete Release**
```bash
# Full automated release (test, tag, package)
python3 tools/release_manager.py release
```

---

## 🚀 **Complete Release Process**

### **1. Development Phase**
```bash
# Work in dev branch
git checkout dev

# Make changes, commit regularly
git add .
git commit -m "Improve camera handling"

# Test frequently  
python3 tools/release_manager.py test
```

### **2. Pre-Release Testing**
```bash
# Ensure dev branch is tested
python3 tools/test_camera_service.py
python3 tools/test_web_service.py
python3 tools/test_smb_service.py

# Run full test suite
python3 tools/release_manager.py test
```

### **3. Release Preparation**
```bash
# Merge dev to main
git checkout main
git merge dev

# Prepare release (choose version bump)
python3 tools/release_manager.py prepare minor

# Review changes, test again
python3 tools/release_manager.py test
```

### **4. Build and Release**
```bash
# Build distribution package
python3 tools/release_manager.py build

# Complete release (creates tag, final package)
python3 tools/release_manager.py release
```

---

## 📦 **What Gets Created**

### **Version Management**
- `VERSION` file updated automatically
- Git tag created (e.g., `v1.2.3`)
- Commit with version bump

### **Distribution Package**
```
dist/
├── PyRpiCamController-1.2.3.zip     # Main distribution
├── PyRpiCamController-1.2.3.zip.sha256  # Checksum
└── release-notes-1.2.3.md          # Release documentation
```

### **Package Contents**
```
PyRpiCamController-1.2.3.zip
├── CamController/          # Core camera code
├── Settings/              # Settings management  
├── Services/              # Systemd services
├── tools/                 # Installation & test scripts
├── webgui/               # Web interface
├── ota/                  # OTA update system  
├── VERSION               # Version file
├── LICENSE               # License
└── readme.adoc           # Documentation
```

---

## 🧪 **Testing Pipeline**

The release manager runs comprehensive tests:

### **Automated Tests**
- ✅ **Python syntax** - Code compilation check
- ✅ **Settings validation** - Settings schema check
- ✅ **Service files** - Systemd service validation  
- ✅ **SMB configuration** - Samba config syntax

### **Manual Pi Testing** (after packaging)
```bash
# Deploy to Pi and test
python3 tools/test_camera_service.py
python3 tools/test_web_service.py  
python3 tools/test_smb_service.py
```

---

## 🔧 **Example Complete Workflow**

### **Scenario: Adding new camera feature**
```bash
# 1. Development
git checkout dev
git checkout -b feature/camera-zoom
# ... implement zoom feature ...
git add .
git commit -m "Add camera zoom functionality"
python3 tools/release_manager.py test  # Test changes

# 2. Integration  
git checkout dev
git merge feature/camera-zoom
git push origin dev

# 3. Pre-release testing
python3 tools/test_camera_service.py  # Test on Pi hardware

# 4. Release preparation
git checkout main
git merge dev
python3 tools/release_manager.py prepare minor  # 1.0.0 → 1.1.0

# 5. Final release
python3 tools/release_manager.py build
python3 tools/release_manager.py release

# 6. Distribution ready!
ls dist/
# PyRpiCamController-1.1.0.zip
# PyRpiCamController-1.1.0.zip.sha256  
# release-notes-1.1.0.md
```

---

## 🎯 **Integration with OTA System**

The release packages are designed for OTA updates:

### **OTA Preparation**
1. **Version detection** - OTA reads VERSION file
2. **Package validation** - SHA256 checksums
3. **Staged deployment** - Test before activation
4. **Rollback capability** - Revert if issues

### **OTA Distribution**
```bash
# Upload to OTA server
scp dist/PyRpiCamController-1.1.0.zip ota-server:/releases/
scp dist/PyRpiCamController-1.1.0.zip.sha256 ota-server:/releases/

# Update OTA database
curl -X POST ota-server/api/releases \
  -d '{"version":"1.1.0","file":"PyRpiCamController-1.1.0.zip"}'
```

---

## 📊 **Benefits of This Approach**

- ✅ **Automated testing** - Catches issues before release
- ✅ **Consistent versioning** - Semantic versioning standard
- ✅ **Clean git history** - Clear release points
- ✅ **Distribution ready** - Zip packages for deployment  
- ✅ **OTA compatible** - Designed for remote updates
- ✅ **Rollback safe** - Git tags enable easy rollbacks
- ✅ **Documentation** - Automatic release notes generation

This workflow ensures reliable, tested releases ready for both manual deployment and OTA distribution! 🚀
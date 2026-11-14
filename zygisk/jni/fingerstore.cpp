// FingerStore optional Zygisk runtime bridge.
// Applies ONLY the selected android.os.Build.FINGERPRINT in newly forked app
// processes, ONLY when enabled by the user, and ONLY in runtime apply mode.
// Does not modify system_server, install hooks or edit global properties.
#include <sys/types.h> // dev_t and ino_t required by the upstream public Zygisk API
#include "zygisk.hpp"
#include <fcntl.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

namespace {
constexpr size_t kMaxConfig = 8192;
constexpr size_t kMaxFingerprint = 240;

bool read_value(int directory, const char *file, const char *key,
                char *out, size_t capacity) {
    if (directory < 0 || !file || !key || capacity < 2) return false;
    const int fd = openat(directory, file, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return false;
    char input[kMaxConfig + 1];
    const ssize_t bytes = read(fd, input, kMaxConfig + 1);
    close(fd);
    if (bytes <= 0 || bytes > static_cast<ssize_t>(kMaxConfig)) return false;
    input[bytes] = '\0';
    const size_t key_len = strlen(key);
    const char *cursor = input;
    const char *end = input + bytes;
    while (cursor < end) {
        const char *newline = static_cast<const char *>(memchr(cursor, '\n', end - cursor));
        const char *limit = newline ? newline : end;
        if (static_cast<size_t>(limit - cursor) > key_len &&
                memcmp(cursor, key, key_len) == 0 && cursor[key_len] == '=') {
            const char *value = cursor + key_len + 1;
            const size_t length = static_cast<size_t>(limit - value);
            if (length == 0 || length >= capacity) return false;
            memcpy(out, value, length);
            out[length] = '\0';
            return true;
        }
        cursor = newline ? newline + 1 : end;
    }
    return false;
}

bool valid_fingerprint(const char *value) {
    const size_t n = strnlen(value, kMaxFingerprint + 1);
    if (n < 16 || n > kMaxFingerprint) return false;
    int slashes = 0, colons = 0;
    for (size_t i = 0; i < n; ++i) {
        const char c = value[i];
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '-') continue;
        if (c == '/') { ++slashes; continue; }
        if (c == ':') { ++colons; continue; }
        return false;
    }
    return slashes == 5 && colons == 2;
}

bool is_true(int dir, const char *path, const char *key) {
    char value[8] = {};
    return read_value(dir, path, key, value, sizeof(value)) && strcmp(value, "1") == 0;
}

bool is_runtime(int dir) {
    char value[24] = {};
    // Runtime-only: a staged reboot selection must never trigger Zygisk.
    return read_value(dir, "config.conf", "apply_mode", value, sizeof(value)) &&
           strcmp(value, "runtime") == 0;
}

class FingerStoreModule : public zygisk::ModuleBase {
public:
    void onLoad(zygisk::Api *api, JNIEnv *env) override {
        api_ = api;
        env_ = env;
    }
    void preAppSpecialize(zygisk::AppSpecializeArgs *args) override {
        // We do not leave hooks behind, so unload the module after specializing.
        api_->setOption(zygisk::DLCLOSE_MODULE_LIBRARY);
        if (args->uid < 10000) return;
        if (api_->getFlags() & zygisk::PROCESS_ON_DENYLIST) return;
        int module_fd = api_->getModuleDir();
        if (module_fd < 0) return;
        const bool enabled =
            is_true(module_fd, "zygisk.conf", "enabled") &&
            is_true(module_fd, "config.conf", "enabled") &&
            is_runtime(module_fd) &&
            read_value(module_fd, "config.conf", "fingerprint",
                       fingerprint_, sizeof(fingerprint_)) &&
            valid_fingerprint(fingerprint_);
        close(module_fd);
        active_ = enabled;
    }
    void postAppSpecialize(const zygisk::AppSpecializeArgs *) override {
        if (!active_ || !env_) return;
        jclass build = env_->FindClass("android/os/Build");
        if (!build) { clear_exception(); return; }
        jfieldID field = env_->GetStaticFieldID(build, "FINGERPRINT", "Ljava/lang/String;");
        if (!field) { clear_exception(); env_->DeleteLocalRef(build); return; }
        jstring selected = env_->NewStringUTF(fingerprint_);
        if (selected) {
            env_->SetStaticObjectField(build, field, selected);
            env_->DeleteLocalRef(selected);
        }
        clear_exception();
        env_->DeleteLocalRef(build);
    }
private:
    void clear_exception() {
        // A missing/blocked framework field must never crash target processes.
        if (env_->ExceptionCheck()) env_->ExceptionClear();
    }
    zygisk::Api *api_ = nullptr;
    JNIEnv *env_ = nullptr;
    bool active_ = false;
    char fingerprint_[kMaxFingerprint + 1] = {};
};
} // namespace

REGISTER_ZYGISK_MODULE(FingerStoreModule)

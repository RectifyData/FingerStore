LOCAL_PATH := $(call my-dir)
include $(CLEAR_VARS)
LOCAL_MODULE := fingerstore
LOCAL_SRC_FILES := fingerstore.cpp
LOCAL_CPPFLAGS := -std=c++17 -fno-exceptions -fno-rtti -fno-threadsafe-statics -fvisibility=hidden -Wall -Wextra -Werror
LOCAL_CFLAGS := -fvisibility=hidden
LOCAL_LDFLAGS := -Wl,--exclude-libs,ALL
include $(BUILD_SHARED_LIBRARY)

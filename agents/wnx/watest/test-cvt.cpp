// test-cvt.cpp :
//ini -> yml

#include "pch.h"

#include <filesystem>

#include "tools/_misc.h"
#include "tools/_process.h"
#include "tools/_tgt.h"

#include "read_file.h"
#include "yaml-cpp/yaml.h"

#include "cvt.h"

#include "read_file.h"

#include "lwa/types.h"

#include "providers/mrpe.h"

#include "test-tools.h"

template <class T>
std::string type_name() {
    typedef typename std::remove_reference<T>::type TR;
    std::unique_ptr<char, void (*)(void*)> own(
#ifndef _MSC_VER
        abi::__cxa_demangle(typeid(TR).name(), nullptr, nullptr, nullptr),
#else
        nullptr,
#endif
        std::free);
    std::string r = own != nullptr ? own.get() : typeid(TR).name();
    if (std::is_const<TR>::value) r += " const";
    if (std::is_volatile<TR>::value) r += " volatile";
    if (std::is_lvalue_reference<T>::value)
        r += "&";
    else if (std::is_rvalue_reference<T>::value)
        r += "&&";
    return r;
}

// clang-format off
//  { "global", "port", int},
//  { "global", "realtime_port", int},
//  { "global", "realtime_timeout", int},
//  { "global", "crash_debug", bool},
//  { "global", "section_flush", bool},
//  { "global", "encrypted", bool},
//  { "global", "encrypted_rt", bool},
//  { "global", "ipv6", bool},
//  { "global", "passphrase", std::string}

// SPLITTED LIST of ipspec
//  { "global", "only_from", std::vector<ipspec>,                BlockMode::FileExclusive, AddMode::Append}

// SPLITTED LIST of strings
// { "global", "sections", std::set<class std::string>,          BlockMode::BlockExclusive, AddMode::SetInserter}
// { "global", "disabled_sections", std::set<class std::string>, BlockMode::BlockExclusive, AddMode::SetInserter}
// { "global", "realtime_sections", std::set<class std::string>, BlockMode::BlockExclusive, AddMode::SetInserter}

// NOT USED
//{ "local", "include",  KeyedListConfigurable<std::string> }
//{ "plugin", "include", KeyedListConfigurable<std::string> }


// { "winperf", "counters", class std::vector<struct winperf_counter>, class BlockMode::Nop, class AddMode::Append}

// { "ps",     "use_wmi",    bool }
// { "ps",     "full_path",  bool }


// { "fileinfo", "path", class std::vector<std::filesystem::path>, class BlockMode::Nop, class AddMode::PriorityAppend }

// { "logwatch", "sendall",   bool}
// { "logwatch", "vista_api", bool}

// { "logwatch", "logname", std::vector<eventlog::config>, BlockMode::Nop, AddMode::PriorityAppend}
// { "logwatch", "logfile", std::vector<eventlog::config>, BlockMode::Nop, AddMode::PriorityAppend}


// { "logfiles", "textfile", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "warn", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "crit", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "ignore", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}
// { "logfiles", "ok", std::vector<struct globline_container>, class BlockMode::Nop, AddMode::PriorityAppendGrouped}

// { "global", "caching_method", class Configurable<enum script_execution_mode>& Value}
// { "global", "async_script_execution", class Configurable<enum script_async_execution>& Value}


// { "global", "execute", <std::vector<std::string>, class BlockMode::BlockExclusive, class AddMode::Append}

// { "local", "timeout", class KeyedListConfigurable<int>}
// { "local", "cache_age", class KeyedListConfigurable<int>}
// { "local", "retry_count", class KeyedListConfigurable<int>}
// { "local", "execution", class KeyedListConfigurable<enum script_execution_mode>}


// { "mrpe", "check", std::vector<mrpe_entry>, BlockMode::Nop, AddMode::Append }
// { "mrpe", "include", KeyedListConfigurable<std::string>}
// clang-format on

#include "cvt.h"

template <typename T>
void printType(T x) {
    std::cout << type_name<T>();
}

namespace cma::cfg::cvt {

void AddKeyedPattern(YAML::Node Node, const std::string Key,
                     const std::string& Pattern, const std::string& Value);

TEST(CvtTest, Keyed) {
    auto result = ToYamlKeyedString("key", "pattern", "0");
    EXPECT_EQ(result, "pattern: 'pattern'\nkey: 0");

    YAML::Node y;
    y["plugins"]["enabled"] = true;
    auto y_exec = y["execution"];

    AddKeyedPattern(y_exec, "k1", "p1", "v1");
    AddKeyedPattern(y_exec, "k2", "p1", "v2");
    AddKeyedPattern(y_exec, "k1", "p2", "v1");
    ASSERT_EQ(y_exec.size(), 2);
    EXPECT_EQ(y_exec[0]["pattern"].as<std::string>(), "p1");
    EXPECT_EQ(y_exec[0]["k1"].as<std::string>(), "v1");
    EXPECT_EQ(y_exec[0]["k2"].as<std::string>(), "v2");
    EXPECT_EQ(y_exec[1]["pattern"].as<std::string>(), "p2");
    EXPECT_EQ(y_exec[1]["pattern"].as<std::string>(), "p2");
    EXPECT_EQ(y_exec[1]["k1"].as<std::string>(), "v1");
}  // namespace cma::cfg::cvt

TEST(CvtTest, ToYaml) {
    winperf_counter z(0, "this_name", "this base id");

    auto s = ToYamlString(z, false);
    EXPECT_EQ(s, "- id: this base id\n  name: this_name\n");

    auto s2 = ToYamlString("aaaa", false);
    EXPECT_EQ(s2, "aaaa");

    auto s3 = ToYamlString("aaaa", true);
    EXPECT_EQ(s3, "- aaaa");
}

TEST(CvtTest, LogFilesSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.logfiles.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLogFiles].IsMap());
        auto logfiles = ya[groups::kLogFiles];
        ASSERT_TRUE(logfiles.IsMap());
        EXPECT_TRUE(logfiles[vars::kEnabled].as<bool>());

        EXPECT_TRUE(logfiles[vars::kLogFilesConfig].size() == 6);
        auto cfgs = logfiles[vars::kLogFilesConfig];

        EXPECT_TRUE(!cfgs[0][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[1][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[2][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[3][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[4][vars::kLogFilesGlob].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[5][vars::kLogFilesGlob].as<std::string>().empty());

        EXPECT_TRUE(!cfgs[0][vars::kLogFilesPattern].as<std::string>().empty());
        EXPECT_TRUE(!cfgs[1][vars::kLogFilesPattern].as<std::string>().empty());
        EXPECT_TRUE(cfgs[2][vars::kLogFilesPattern].IsNull());
        EXPECT_TRUE(cfgs[3][vars::kLogFilesPattern].IsNull());
        EXPECT_TRUE(cfgs[4][vars::kLogFilesPattern].IsNull());
        EXPECT_TRUE(cfgs[5][vars::kLogFilesPattern].IsNull());
    }
}

TEST(CvtTest, LogWatchSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.logwatch.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLogWatchEvent].IsMap());
        auto logwatch = ya[groups::kLogWatchEvent];
        ASSERT_TRUE(logwatch.IsMap());
        EXPECT_TRUE(logwatch[vars::kEnabled].as<bool>());
        EXPECT_TRUE(logwatch[vars::kLogWatchEventSendall].as<bool>());
        EXPECT_TRUE(logwatch[vars::kLogWatchEventVistaApi].as<bool>());

        EXPECT_TRUE(logwatch[vars::kLogWatchEventLogFile].size() == 4);
        auto logfiles = logwatch[vars::kLogWatchEventLogFile];
        EXPECT_EQ(logfiles[0][vars::kLogWatchEvent_Name].as<std::string>(),
                  "application");
        EXPECT_EQ(logfiles[1][vars::kLogWatchEvent_Name].as<std::string>(),
                  "system");
        EXPECT_EQ(logfiles[2][vars::kLogWatchEvent_Name].as<std::string>(),
                  "*");
        EXPECT_EQ(logfiles[3][vars::kLogWatchEvent_Name].as<std::string>(),
                  "microsoft-windows-grouppolicy/operational");

        EXPECT_EQ(logfiles[0][vars::kLogWatchEvent_Context].as<bool>(), true);
        EXPECT_EQ(logfiles[1][vars::kLogWatchEvent_Context].as<bool>(), false);
        EXPECT_EQ(logfiles[2][vars::kLogWatchEvent_Context].as<bool>(), true);
        EXPECT_EQ(logfiles[3][vars::kLogWatchEvent_Context].as<bool>(), true);

        EXPECT_EQ(logfiles[0][vars::kLogWatchEvent_Level].as<std::string>(),
                  vars::kLogWatchEvent_ParamWords[3]);
        EXPECT_EQ(logfiles[1][vars::kLogWatchEvent_Level].as<std::string>(),
                  vars::kLogWatchEvent_ParamWords[2]);
        EXPECT_EQ(logfiles[2][vars::kLogWatchEvent_Level].as<std::string>(),
                  vars::kLogWatchEvent_ParamWords[0]);
        EXPECT_EQ(logfiles[3][vars::kLogWatchEvent_Level].as<std::string>(),
                  vars::kLogWatchEvent_ParamWords[2]);
    }
}

TEST(CvtTest, MrpeSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.mrpe.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kMrpe].IsMap());
        auto mr = ya[groups::kMrpe];
        ASSERT_TRUE(mr.IsMap());
        EXPECT_TRUE(mr[vars::kEnabled].as<bool>());
        EXPECT_TRUE(mr[vars::kMrpeConfig].IsSequence());
        EXPECT_TRUE(mr[vars::kMrpeConfig].size() == 5);
        EXPECT_TRUE(mr[vars::kMrpeConfig].size() == 5);
    }
    cma::provider::MrpeProvider mrpe;
    mrpe.loadConfig();
    auto entries = mrpe.entries();
    ASSERT_EQ(entries.size(), 0);
    auto checks = mrpe.checks();
    ASSERT_EQ(checks.size(), 3);
    auto includes = mrpe.includes();
    ASSERT_EQ(includes.size(), 2);
}

TEST(CvtTest, PluginsLocalSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.plugins_local.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLocal].IsMap());
        auto loc = ya[groups::kLocal];
        ASSERT_TRUE(loc.IsMap());
        EXPECT_TRUE(loc[vars::kEnabled].as<bool>());
        EXPECT_TRUE(loc[vars::kPluginsExecution].IsSequence());
        EXPECT_TRUE(loc[vars::kPluginsExecution].size() == 3);
        auto exec = loc[vars::kPluginsExecution];
        EXPECT_EQ(exec[0][vars::kPluginPattern].as<std::string>(), "*.vbs");
        EXPECT_EQ(exec[1][vars::kPluginPattern].as<std::string>(), "*.bat");
        EXPECT_EQ(exec[2][vars::kPluginPattern].as<std::string>(), "*");

        EXPECT_EQ(exec[0][vars::kPluginTimeout].as<int>(), 20);
        EXPECT_EQ(exec[1][vars::kPluginTimeout].as<int>(), 10);
        EXPECT_EQ(exec[2][vars::kPluginTimeout].as<int>(), 30);
    }
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kLocal].IsMap());
        auto plu = ya[groups::kPlugins];
        ASSERT_TRUE(plu.IsMap());
        EXPECT_TRUE(plu[vars::kEnabled].as<bool>());
        EXPECT_TRUE(plu[vars::kPluginsExecution].IsSequence());
        EXPECT_EQ(plu[vars::kPluginsExecution].size(), 5);
        auto exec = plu[vars::kPluginsExecution];
        EXPECT_EQ(exec[0][vars::kPluginPattern].as<std::string>(),
                  "@user\\windows_updates.vbs");
        EXPECT_EQ(exec[1][vars::kPluginPattern].as<std::string>(),
                  "@user\\mk_inventory.ps1");
        EXPECT_EQ(exec[2][vars::kPluginPattern].as<std::string>(),
                  "@user\\ps_perf.ps1");
        EXPECT_EQ(exec[3][vars::kPluginPattern].as<std::string>(),
                  "@user\\*.ps1");
        EXPECT_EQ(exec[4][vars::kPluginPattern].as<std::string>(), "@user\\*");

        EXPECT_EQ(exec[0][vars::kPluginTimeout].as<int>(), 120);
        EXPECT_EQ(exec[0][vars::kPluginCacheAge].as<int>(), 3600);
        EXPECT_EQ(exec[0][vars::kPluginRetry].as<int>(), 3);
        EXPECT_EQ(exec[0][vars::kPluginAsync].as<bool>(), true);

        EXPECT_EQ(exec[1][vars::kPluginTimeout].as<int>(), 240);
        EXPECT_EQ(exec[1][vars::kPluginAsync].as<bool>(), true);

        EXPECT_EQ(exec[2][vars::kPluginTimeout].as<int>(), 20);
        EXPECT_EQ(exec[3][vars::kPluginTimeout].as<int>(), 10);
        EXPECT_EQ(exec[4][vars::kPluginTimeout].as<int>(), 30);
    }
}

TEST(CvtTest, PsSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.ps.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kPs].IsMap());
        auto ps = ya[groups::kPs];
        ASSERT_TRUE(ps.IsMap());
        {
            EXPECT_FALSE(ps[vars::kPsFullPath].as<bool>());
            EXPECT_FALSE(ps[vars::kPsUseWmi].as<bool>());
            EXPECT_TRUE(ps[vars::kEnabled].as<bool>());
        }
    }
}

TEST(CvtTest, FileInfoSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.fileinfo.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kFileInfo].IsMap());
        auto fi = ya[groups::kFileInfo];
        ASSERT_TRUE(fi.IsMap());
        {
            auto paths = fi[vars::kFileInfoPath];
            ASSERT_TRUE(paths.IsSequence());
            ASSERT_TRUE(paths.size() == 3);
            EXPECT_EQ(paths[0].as<std::string>(), "C:\\Programs\\Foo\\*.log");
            EXPECT_EQ(paths[1].as<std::string>(), "M:\\Bar Test\\*.*");
            EXPECT_EQ(paths[2].as<std::string>(), "C:\\MyDocuments\\Foo\\**");
            EXPECT_TRUE(fi[vars::kEnabled].as<bool>());
        }
    }
}

TEST(CvtTest, WinPerfSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.winperf.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    yaml[groups::kGlobal][vars::kEnabled] =
        true;  // mandatory, otherwise file to be disabled
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kWinPerf].IsMap());
        auto wp = ya[groups::kWinPerf];
        ASSERT_TRUE(wp.IsMap());
        {
            auto counters = wp[vars::kWinPerfCounters];
            ASSERT_TRUE(counters.IsSequence());
            ASSERT_TRUE(counters.size() == 3);
            EXPECT_EQ(counters[0]["id"].as<std::string>(), "10332");
            EXPECT_EQ(counters[0]["name"].as<std::string>(), "msx_queues");
            EXPECT_EQ(counters[1]["id"].as<std::string>(), "638");
            EXPECT_EQ(counters[1]["name"].as<std::string>(), "tcp_conn");
            EXPECT_EQ(counters[2]["id"].as<std::string>(), "Terminal Services");
            EXPECT_EQ(counters[2]["name"].as<std::string>(), "ts_sessions");
            EXPECT_TRUE(wp[vars::kEnabled].as<bool>());
        }
    }
}

TEST(CvtTest, GlobalSection) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.global.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);

    auto yaml = p.emitYaml();
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    // EXPECT_EQ(yaml[kGlobal][kEnabled])
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.yml";
    std::ofstream ofs(temp_file.u8string());
    ofs << yaml;
    ofs.close();
    OnStart(kTest, false, temp_file.wstring());
    std::error_code ec;
    ON_OUT_OF_SCOPE(fs::remove(temp_file, ec); OnStart(kTest));
    {
        auto ya = cma::cfg::GetLoadedConfig();
        ASSERT_TRUE(ya[groups::kGlobal].IsMap());
        auto g = ya[groups::kGlobal];
        ASSERT_TRUE(g.IsMap());
        EXPECT_EQ(g["async_script_execution"].as<std::string>(), "parallel");
        EXPECT_EQ(g[vars::kEnabled].as<bool>(), true);
        {
            auto logging = g[vars::kLogging];
            ASSERT_TRUE(logging.IsMap());
            EXPECT_EQ(logging[vars::kLogDebug].as<std::string>(), "yes");
        }
        {
            auto sections = g[vars::kSectionsEnabled];
            ASSERT_TRUE(sections.IsSequence());
            ASSERT_TRUE(sections.size() == 2);
            EXPECT_EQ(sections[0].as<std::string>(), "check_mk");
            EXPECT_EQ(sections[1].as<std::string>(), groups::kWinPerf);
        }
        {
            auto sessions = g[vars::kSectionsDisabled];
            ASSERT_TRUE(sessions.IsSequence());
            ASSERT_TRUE(sessions.size() == 1);
            EXPECT_EQ(sessions[0].as<std::string>(), groups::kLogFiles);
        }
        {
            auto onlyfrom = g[vars::kOnlyFrom];
            ASSERT_TRUE(onlyfrom.IsSequence());
            ASSERT_TRUE(onlyfrom.size() == 3);
            EXPECT_EQ(onlyfrom[0].as<std::string>(), "127.0.0.1/32");
            EXPECT_EQ(onlyfrom[1].as<std::string>(), "192.168.56.0/24");
            EXPECT_EQ(onlyfrom[2].as<std::string>(), "0:0:0:0:0:0:0:1/128");
        }
        {
            auto onlyfrom = g[vars::kExecute];
            ASSERT_TRUE(onlyfrom.IsSequence());
            ASSERT_TRUE(onlyfrom.size() == 3);
            EXPECT_EQ(onlyfrom[0].as<std::string>(), "exe");
            EXPECT_EQ(onlyfrom[1].as<std::string>(), "bat");
            EXPECT_EQ(onlyfrom[2].as<std::string>(), "vbs");
        }

        {
            EXPECT_EQ(g[vars::kGlobalEncrypt].as<bool>(), false);
            EXPECT_EQ(g[vars::kGlobalPassword].as<std::string>(), "secret");
            EXPECT_EQ(g[vars::kSectionFlush].as<bool>(), false);
            EXPECT_EQ(g[vars::kPort].as<int>(), 6556);
            EXPECT_EQ(g[vars::kIpv6].as<bool>(), false);
        }

        {
            auto rt = g[vars::kRealTime];
            ASSERT_TRUE(rt.IsMap());
            EXPECT_EQ(rt[vars::kTimeout].as<int>(), 90);
            EXPECT_EQ(rt[vars::kRtEncrypt].as<bool>(), true);
            auto rt_sessions = rt[vars::kRtRun];
            ASSERT_TRUE(rt_sessions.IsSequence());
            ASSERT_TRUE(rt_sessions.size() == 3);
            EXPECT_EQ(rt_sessions[0].as<std::string>(), "df");
            EXPECT_EQ(rt_sessions[1].as<std::string>(), "mem");
            EXPECT_EQ(rt_sessions[2].as<std::string>(), "winperf_processor");
        }
    }
}

TEST(CvtTest, BaseCall) {
    namespace fs = std::filesystem;
    fs::path test_file = cma::cfg::GetUserDir();
    test_file /= "check_mk.test.ini";
    Parser p;
    p.prepare();
    p.readIni(test_file, false);
    fs::path temp_file = cma::cfg::GetTempDir();
    temp_file /= "temp.check.out";

    std::error_code ec;
    fs::remove(temp_file, ec);
    // ON_OUT_OF_SCOPE(fs::remove(temp_file, ec););
    std::ofstream out(temp_file);
    p.emitYaml(out);
    out.close();
    auto emitted = cma::tools::ReadFileInVector(temp_file);

    fs::path base_file = cma::cfg::GetUserDir();
    base_file /= "check_mk.test.out";
    ASSERT_TRUE(fs::exists(base_file, ec));

    auto expected = cma::tools::ReadFileInVector(base_file);
    EXPECT_EQ(emitted, expected);

    auto res = CheckIniFile(test_file);
    EXPECT_TRUE(res);

    auto yaml = p.emitYaml();
    EXPECT_TRUE(yaml.IsDefined() && yaml.IsMap());
    tst::SafeCleanTempDir();
}

}  // namespace cma::cfg::cvt

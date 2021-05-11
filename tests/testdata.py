testdata = {
    "py": [
        {
            "test_name": "simple_a",
            "directory": "simple_a",
            "expected_edges": [["simple_a::func_a", "simple_a::func_b"]],
            "expected_nodes": ["simple_a::func_a", "simple_a::func_b"]
        },
        {
            "test_name": "simple_b",
            "directory": "simple_b",
            "expected_edges": [
                ["simple_b::c.d", "simple_b::a"],
                ["simple_b::a", "simple_b::b"],
                ["simple_b::(global)", "simple_b::c.d"],
                ["simple_b::b", "simple_b::a"]],
            "expected_nodes": ["simple_b::c.d", "simple_b::a", "simple_b::b",
                               "simple_b::(global)"]
        },
        {
            "test_name": "simple_b --exclude-functions",
            "comment": "We don't have a function c so nothing should happen",
            "directory": "simple_b",
            "kwargs": {"exclude_functions": ["c"]},
            "expected_edges": [
                ["simple_b::c.d", "simple_b::a"],
                ["simple_b::a", "simple_b::b"],
                ["simple_b::(global)", "simple_b::c.d"],
                ["simple_b::b", "simple_b::a"]
            ],
            "expected_nodes": ["simple_b::c.d", "simple_b::a", "simple_b::b",
                               "simple_b::(global)"]
        },
        {
            "test_name": "simple_b --exclude-functions2",
            "comment": "Exclude all edges with function a",
            "directory": "simple_b",
            "kwargs": {"exclude_functions": ["a"]},
            "expected_edges": [
                ["simple_b::(global)", "simple_b::c.d"]
            ],
            "expected_nodes": ["simple_b::c.d", "simple_b::(global)"]
        },
        {
            "test_name": "simple_b --exclude-functions2 no_trimming",
            "comment": "Exclude all edges with function a. No trimming keeps nodes except a",
            "directory": "simple_b",
            "kwargs": {"exclude_functions": ["a"], "no_trimming": True},
            "expected_edges": [
                ["simple_b::(global)", "simple_b::c.d"]
            ],
            "expected_nodes": ["simple_b::c.d", "simple_b::b", "simple_b::(global)"]
        },
        {
            "test_name": "simple_b --exclude-functions2",
            "comment": "Exclude all edges with function d (d is in a class)",
            "directory": "simple_b",
            "kwargs": {"exclude_functions": ["d"]},
            "expected_edges": [
                ["simple_b::a", "simple_b::b"],
                ["simple_b::b", "simple_b::a"]
            ],
            "expected_nodes": ["simple_b::a", "simple_b::b"]
        },
        {
            "test_name": "simple_b --exclude-namespaces",
            "comment": "Exclude the file itself",
            "directory": "simple_b",
            "kwargs": {"exclude_namespaces": ["simple_b"]},
            "expected_edges": [],
            "expected_nodes": []
        },
        {
            "test_name": "simple_b --exclude-namespaces 2",
            "comment": "Exclude a class in the file",
            "directory": "simple_b",
            "kwargs": {"exclude_namespaces": ["c"]},
            "expected_edges": [
                ["simple_b::a", "simple_b::b"],
                ["simple_b::b", "simple_b::a"]
            ],
            "expected_nodes": ["simple_b::a", "simple_b::b"]
        },
        {
            "test_name": "simple_b --exclude-namespaces not found",
            "comment": "Exclude something not there",
            "directory": "simple_b",
            "kwargs": {"exclude_namespaces": ["notreal"]},
            "expected_edges": [
                ["simple_b::c.d", "simple_b::a"],
                ["simple_b::a", "simple_b::b"],
                ["simple_b::(global)", "simple_b::c.d"],
                ["simple_b::b", "simple_b::a"]
            ],
            "expected_nodes": ["simple_b::c.d", "simple_b::a", "simple_b::b",
                               "simple_b::(global)"]
        },
        {
            "test_name": "two_file_simple",
            "directory": "two_file_simple",
            "expected_edges": [["file_a::(global)", "file_a::a"],
                               ["file_a::a", "file_b::b"]],
            "expected_nodes": ["file_a::(global)", "file_a::a", "file_b::b"]
        },
        {
            "test_name": "two_file_simple --exclude_functions",
            "comment": "Function a is in both files so should be removed from both",
            "directory": "two_file_simple",
            "kwargs": {"exclude_functions": ["a"]},
            "expected_edges": [],
            "expected_nodes": []
        },
        {
            "test_name": "two_file_simple --exclude_functions no-trim",
            "comment": "Function a is in both files but don't trim so leave file_b nodes",
            "directory": "two_file_simple",
            "kwargs": {"exclude_functions": ["a"], "no_trimming": True},
            "expected_edges": [],
            "expected_nodes": ["file_a::(global)", "file_b::(global)", "file_b::b", "file_b::c"]
        },
        {
            "test_name": "two_file_simple --exclude_namespaces no-trim",
            "comment": "Trim one file and leave the other intact",
            "directory": "two_file_simple",
            "kwargs": {"exclude_namespaces": ["file_a"], "no_trimming": True},
            "expected_edges": [],
            "expected_nodes": ["file_b::(global)", "file_b::b", "file_b::c"]
        },
        {
            "test_name": "exclude_modules",
            "comment": "Correct name resolution when third-party modules are involved",
            "directory": "exclude_modules",
            "kwargs": {},
            "expected_edges": [["exclude_modules::(global)", "exclude_modules::alpha"],
                               ["exclude_modules::alpha", "exclude_modules::beta"],
                               ["exclude_modules::beta", "exclude_modules::search"]],
            "expected_nodes": ["exclude_modules::(global)", "exclude_modules::alpha",
                               "exclude_modules::beta", "exclude_modules::search"]
        },
        {
            "test_name": "exclude_modules_two_files",
            "comment": "TODO Correct name resolution when third-party modules are involved with two files",
            "directory": "exclude_modules_two_files",
            "kwargs": {},
            "expected_edges": [],
            "expected_nodes": []
        },
        {
            "test_name": "resolve_correct_class",
            "comment": "Correct name resolution with multiple classes",
            "directory": "resolve_correct_class",
            "kwargs": {},
            "expected_edges": [["rcc::Alpha.func_1", "rcc::Alpha.func_1"],
                               ["rcc::Alpha.func_1", "rcc::func_1"],
                               ["rcc::Alpha.func_1", "rcc::Beta.func_2"],
                               ["rcc::Beta.func_1", "rcc::Alpha.func_2"],
                               ],
            "expected_nodes": ["rcc::Alpha.func_1", "rcc::Alpha.func_2",
                               "rcc::func_1", "rcc::Beta.func_2",
                               "rcc::Beta.func_1"]
        },
        {
            "test_name": "ambibuous resolution",
            "comment": "If we can't resolve, do not inlude node.",
            "directory": "ambiguous_resolution",
            "expected_edges": [["ambiguous_resolution::(global)",
                                "ambiguous_resolution::main"],
                               ["ambiguous_resolution::main",
                                "ambiguous_resolution::Cadabra.cadabra_it"],
                               ["ambiguous_resolution::Cadabra.cadabra_it",
                                "ambiguous_resolution::Abra.abra_it"]],
            "expected_nodes": ["ambiguous_resolution::(global)",
                               "ambiguous_resolution::main",
                               "ambiguous_resolution::Cadabra.cadabra_it",
                               "ambiguous_resolution::Abra.abra_it"]
        },
        {
            "test_name": "weird_imports",
            "directory": "weird_imports",
            "expected_edges": [["weird_imports::(global)", "weird_imports::main"]],
            "expected_nodes": ["weird_imports::main", "weird_imports::(global)"]
        },
        {
            "test_name": "nested classes",
            "directory": "nested_class",
            "expected_edges": [["nested_class::(global)",
                                "nested_class::Outer.outer_func"]],
            "expected_nodes": ["nested_class::Outer.outer_func", "nested_class::(global)"]
        },
        {
            "test_name": "weird_calls",
            "directory": "weird_calls",
            "comment": "Subscript calls",
            "expected_edges": [["weird_calls::func_c", "weird_calls::print_it"],
                               ["weird_calls::func_b", "weird_calls::print_it"],
                               ["weird_calls::(global)", "weird_calls::func_b"],
                               ["weird_calls::func_a", "weird_calls::print_it"],
                               ["weird_calls::(global)", "weird_calls::factory"]],
            "expected_nodes": ["weird_calls::func_b",
                               "weird_calls::print_it",
                               "weird_calls::(global)",
                               "weird_calls::func_c",
                               "weird_calls::func_a",
                               "weird_calls::factory"]
        },
        {
            "test_name": "pytz",
            "directory": "pytz",
            "kwargs": {"exclude_namespaces": ["test_tzinfo"]},
            "expected_edges": [["tzinfo::DstTzInfo.tzname", "tzinfo::DstTzInfo.localize"],
                               ["tzfile::build_tzinfo", "tzinfo::memorized_timedelta"],
                               ["reference::LocalTimezone.tzname",
                                "reference::LocalTimezone._isdst"],
                               ["reference::USTimeZone.dst",
                                "reference::first_sunday_on_or_after"],
                               ["tzinfo::unpickler", "tzinfo::memorized_timedelta"],
                               ["__init__::timezone", "tzfile::build_tzinfo"],
                               ["tzfile::build_tzinfo", "tzfile::_byte_string"],
                               ["__init__::resource_exists", "__init__::open_resource"],
                               ["__init__::(global)", "__init__::_test"],
                               ["__init__::UTC.fromutc", "__init__::UTC.localize"],
                               ["__init__::_CountryTimezoneDict._fill",
                                "__init__::open_resource"],
                               ["__init__::timezone", "__init__::open_resource"],
                               ["__init__::timezone", "__init__::ascii"],
                               ["tzfile::(global)", "tzfile::_byte_string"],
                               ["tzinfo::DstTzInfo.localize",
                                "tzinfo::DstTzInfo.localize"],
                               ["tzinfo::memorized_ttinfo", "tzinfo::memorized_timedelta"],
                               ["tzfile::build_tzinfo", "tzinfo::memorized_ttinfo"],
                               ["tzinfo::(global)", "tzinfo::memorized_timedelta"],
                               ["reference::LocalTimezone.dst",
                                "reference::LocalTimezone._isdst"],
                               ["__init__::_p", "tzinfo::unpickler"],
                               ["tzfile::build_tzinfo", "tzfile::_std_string"],
                               ["__init__::_CountryNameDict._fill",
                                "__init__::open_resource"],
                               ["tzfile::(global)", "tzfile::build_tzinfo"],
                               ["reference::USTimeZone.utcoffset",
                                "reference::USTimeZone.dst"],
                               ["__init__::timezone", "__init__::_unmunge_zone"],
                               ["tzinfo::DstTzInfo.normalize",
                                "tzinfo::DstTzInfo.fromutc"],
                               ["lazy::LazyDict.keys", "lazy::LazyDict.keys"],
                               ["tzfile::build_tzinfo", "tzinfo::memorized_datetime"],
                               ["__init__::timezone",
                                "__init__::_case_insensitive_zone_lookup"],
                               ["reference::LocalTimezone.utcoffset",
                                "reference::LocalTimezone._isdst"],
                               ["reference::USTimeZone.tzname",
                                "reference::USTimeZone.dst"],
                               ["tzinfo::DstTzInfo.dst", "tzinfo::DstTzInfo.localize"],
                               ["tzinfo::DstTzInfo.utcoffset",
                                "tzinfo::DstTzInfo.localize"],
                               ["tzinfo::DstTzInfo.__reduce__", "tzinfo::_to_seconds"]],
            "expected_nodes": ["tzfile::_std_string",
                               "reference::USTimeZone.tzname",
                               "__init__::_p",
                               "tzinfo::memorized_ttinfo",
                               "__init__::_test",
                               "tzfile::_byte_string",
                               "tzinfo::DstTzInfo.dst",
                               "reference::LocalTimezone._isdst",
                               "tzinfo::unpickler",
                               "reference::LocalTimezone.utcoffset",
                               "__init__::ascii",
                               "reference::USTimeZone.dst",
                               "tzinfo::DstTzInfo.fromutc",
                               "__init__::resource_exists",
                               "tzinfo::DstTzInfo.__reduce__",
                               "lazy::LazyDict.keys",
                               "tzinfo::(global)",
                               "tzinfo::memorized_datetime",
                               "reference::LocalTimezone.tzname",
                               "__init__::_CountryNameDict._fill",
                               "tzinfo::memorized_timedelta",
                               "tzfile::(global)",
                               "__init__::UTC.fromutc",
                               "__init__::open_resource",
                               "__init__::_CountryTimezoneDict._fill",
                               "reference::USTimeZone.utcoffset",
                               "reference::first_sunday_on_or_after",
                               "__init__::timezone",
                               "tzinfo::DstTzInfo.utcoffset",
                               "tzinfo::DstTzInfo.localize",
                               "__init__::(global)",
                               "tzinfo::DstTzInfo.tzname",
                               "tzinfo::_to_seconds",
                               "reference::LocalTimezone.dst",
                               "tzfile::build_tzinfo",
                               "__init__::_unmunge_zone",
                               "__init__::UTC.localize",
                               "__init__::_case_insensitive_zone_lookup",
                               "tzinfo::DstTzInfo.normalize"]        },
    ],
    "js": [

    ]
}

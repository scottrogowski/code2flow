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

    ],
    "js": [
        {
            "test_name": "simple_a_js",
            "directory": "simple_a_js",
            "expected_edges": [["simple_a::func_a", "simple_a::func_b"]],
            "expected_nodes": ["simple_a::func_a", "simple_a::func_b"]
        },
        {
            "test_name": "simple_b_js",
            "directory": "simple_b_js",
            "expected_edges": [
                ["simple_b::C.d", "simple_b::a"],
                ["simple_b::a", "simple_b::b"],
                ["simple_b::(global)", "simple_b::C.d"],
                ["simple_b::b", "simple_b::a"]],
            "expected_nodes": ["simple_b::C.d", "simple_b::a", "simple_b::b",
                               "simple_b::(global)"]
        },
        {
            "test_name": "two_file_simple",
            "directory": "two_file_simple",
            "expected_edges": [["file_a::(global)", "file_a::a"],
                               ["file_a::a", "file_b::b"]],
            "expected_nodes": ["file_a::(global)", "file_a::a", "file_b::b"]
        },
    ]
}

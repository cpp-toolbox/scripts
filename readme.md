# setup
* run `python scripts/setup/main.py` from the root project directory which will setup up the project and build the project

# setup details:
* cpp_project_bootstrapper: (sets up a conanfile.txt and CMakeLists.txt with mwe main.cpp)
* sbpt: if the project uses cpp-toolbox subprojects, then you should run this
* clang_formatting: run the copy files script to get the formatting and setup where clangd will look for the compile commands

# working
* build_notifier: easy ways to run command cmake build commands
* cpp_toolbox_submodule_adder: add in existing submodules quickly to the project
* cpp_file_generator: to quickly create header and source files, avoiding writing boilerplate code
* process_changes_in_submodules: automatically moves you to all submodules for easy committing use ctrl-d to exit the subprocess

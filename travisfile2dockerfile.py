import argparse
import itertools
import os
import re
import shutil
import stat
import subprocess
import types
from sys import stdout
from tempfile import gettempdir

import yaml


class git(object):

    def __init__(self, repo_git, path):
        self.repo_git = repo_git
        self.path = path

    def run(self, cmd):
        """Execute git command in bash"""
        cmd = ['git', '--git-dir=%s' % self.path] + cmd
        # print "cmd", ' '.join(cmd)
        try:
            return subprocess.check_output(cmd)
        except BaseException:
            return None

    def update(self):
        """Get a repository git or update it"""
        if not os.path.isdir(os.path.join(self.path)):
            os.makedirs(self.path)
        if not os.path.isdir(os.path.join(self.path, 'refs')):
            subprocess.check_output([
                'git', 'clone', '--bare', self.repo_git, self.path
            ])
        self.run(['gc', '--auto', '--prune=all'])
        self.run(['fetch', '-p', 'origin', '+refs/heads/*:refs/heads/*'])
        self.run(['fetch', '-p', 'origin', '+refs/pull/*/head:refs/pull/*'])

    def show_file(self, git_file, sha):
        result = self.run(["show", "%s:%s" % (sha, git_file)])
        return result


# TODO: Change name of class and variables to cmd
class travis(object):

    def load_travis_file(self, branch):
        self.git_obj.update()
        yaml_loaded = None
        for fname in ['.travis.yml', '.shippable.yml']:
            yaml_str = self.git_obj.show_file(fname, branch)
            try:
                yaml_loaded = yaml.load(yaml_str)
                break
            except AttributeError:
                pass
        return yaml_loaded

    def get_folder_name(self, name):
        for invalid_char in '@:/':
            name = name.replace(invalid_char, '_')
        return name

    def get_repo_path(self, root_path):
        name = self.get_folder_name(self.git_project)
        repo_path = os.path.join(root_path, 'repo', name)
        return repo_path

    def get_script_path(self, root_path):
        name = self.get_folder_name(self.git_project)
        script_path = os.path.join(
            root_path, 'script',
            name, self.get_folder_name(self.git_sha))
        return script_path

    def __init__(self, git_project, git_sha,
                 command_format='docker', docker_user=None,
                 git_root_path=None, scripts_root_path=None):
        """
        Method Constructor
        @fname_dockerfile: str name of file dockerfile to save.
        @format_cmd: str name of format of command.
                     bash: Make a bash script.
                     docker: Make a dockerfile script.
        """
        if git_root_path is None:
            git_root_path = gettempdir()
        self.git_project = git_project
        self.git_sha = git_sha
        git_path = self.get_repo_path(git_root_path)
        self.git_obj = git(git_project, git_path)
        self.travis_data = self.load_travis_file(git_sha)
        if not self.travis_data:
            raise Exception(
                "No yaml file loaded in %s of %s" % (
                    git_sha, git_project)
            )
        self.travis2docker_section = [
            # ('build_image', 'build_image'),
            ('python', 'python'),
            ('env', 'env'),
            ('install', 'run'),
            ('script', 'script'),
        ]
        self.travis2docker_section_dict = dict(self.travis2docker_section)
        if scripts_root_path is None:
            self.scripts_root_path = self.get_script_path(git_root_path)
        else:
            self.scripts_root_path = scripts_root_path
        env_regex_str = r"(?P<var>[\w]*)[ ]*[\=][ ]*[\"\']{0,1}" + \
            r"(?P<value>[\w\.\-\_/\$\{\}\:]*)[\"\']{0,1}"
        export_regex_str = r"(?P<export>export|EXPORT)( )+" + env_regex_str
        self.env_regex = re.compile(env_regex_str, re.M)
        self.export_regex = re.compile(export_regex_str, re.M)
        self.extra_env_from_run = ""
        self.command_format = command_format
        self.docker_user = docker_user or 'root'

    # def get_travis_type(self, repo_git):
    #     self.repo_git_type = None
    #     if os.path.isdir(repo_git):
    #         self.repo_git_type = 'localpath'
    #     elif os.path.isfile(repo_git):
    #         self.repo_git_type = 'file'
    #     else:
    #         regex = r"(?P<host>(git@|https://)([\w\.@]+)(/|:))" \
    #                  r"(?P<owner>[~\w,\-,\_]+)/" \
    #                  r"(?P<repo>[\w,\-,\_]+)(.git){0,1}((/){0,1})"
    #         match_object = re.search(regex, repo_git)
    #         if match_object:
    #             self.repo_git_type = 'remote'

    # def get_travis_data(self, repo_git, branch=None):
    #     self.get_travis_type(repo_git)
    #     if self.repo_git_type == 'remote':
    #         if branch is None:
    #             raise "You need specify branch name with remote repository"
    #         "git show 8.0:.travis.yml"

    def get_travis_section(self, section):
        section_type = self.travis2docker_section_dict.get(section, False)
        if not section_type:
            return None
        section_data = self.travis_data.get(section, "")
        if isinstance(section_data, basestring):
            section_data = [section_data]
        job_method = getattr(self, 'get_travis2docker_' + section_type)
        return job_method(section_data)

    # def get_travis2docker_build_image(self, section_data):
    #     cmd_str = ''
    #     if self.command_format == 'docker':
    #         for line in section_data:
    #             cmd_str = 'FROM ' + line
    #     return cmd_str

    def get_travis2docker_run(self, section_data):
        docker_run = ''
        for line in section_data:
            export_regex_findall = self.export_regex.findall(line)
            for dummy, dummy, var, value in export_regex_findall:
                self.extra_env_from_run += "%s=%s " % (var, value)
            if not export_regex_findall:
                if self.command_format == 'bash':
                    docker_run += '\n' + self.extra_env_from_run + line
                elif self.command_format == 'docker':
                    docker_run += '\nRUN ' + self.extra_env_from_run + line
        return docker_run

    def get_travis2docker_script(self, section_data):
        cmd_str = self.get_travis2docker_run(section_data)
        if self.command_format == 'docker' and cmd_str:
            cmd_str = cmd_str[0] + cmd_str[1:].replace('\nRUN ', ' && ')
            cmd_str = cmd_str.replace('RUN ', 'ENTRYPOINT ')
        return cmd_str

    def get_travis2docker_env(self, section_data):
        for line in section_data:
            docker_env = ""
            for var, value in self.env_regex.findall(line):
                if self.command_format == 'bash':
                    docker_env += "\nexport %s=%s" % (var, value)
                elif self.command_format == 'docker':
                    docker_env += "\nENV %s=%s" % (var, value)
            yield docker_env

    def get_travis2docker_python(self, section_data):
        for line in section_data:
            yield "\n# TODO: Use python version: " + line

    def get_default_cmd(self, dockerfile_path):
        home_user_path = self.docker_user == 'root' and "/root" \
            or os.path.join("/home", self.docker_user)
        project, branch = self.git_project, self.git_sha
        travis_build_dir = os.path.join(home_user_path, "myproject")
        if self.command_format == 'bash':
            cmd = "\nsudo su - " + self.docker_user + \
                  "\nsudo chown -R %s:%s %s" % (self.docker_user, self.docker_user, home_user_path) + \
                  "\nexport TRAVIS_BUILD_DIR=%s" % (travis_build_dir) + \
                  "\ngit clone --single-branch %s -b %s " % (project, branch) + \
                  "${TRAVIS_BUILD_DIR}" + \
                  "\n"
        elif self.command_format == 'docker':
            dkr_files_path = os.path.join(dockerfile_path, "files")
            if not os.path.exists(dkr_files_path):
                os.makedirs(dkr_files_path)
            if not os.path.exists(os.path.join(dkr_files_path, 'ssh')):
                shutil.copytree(
                    os.path.expanduser("~/.ssh"),
                    os.path.join(dkr_files_path, 'ssh')
                )
            cmd = 'FROM ' + self.travis_data.get('build_image', "") + \
                  '\nUSER ' + self.docker_user + \
                  '\nADD ' + os.path.join("files", 'ssh') + ' ' + \
                  os.path.join(home_user_path, '.ssh') + \
                  "\nRUN sudo chown -R %s:%s %s" % (self.docker_user, self.docker_user, home_user_path) + \
                  "\nWORKDIR " + home_user_path + \
                  "\nENV TRAVIS_BUILD_DIR=%s" % (travis_build_dir) + \
                  "\nRUN git clone --single-branch %s -b %s " % (project, branch) + \
                  "${TRAVIS_BUILD_DIR}" + \
                  "\n"
        return cmd

    def get_travis2docker_iter(self):
        travis2docker_cmd_static_str = ""
        travis2docker_cmd_iter_list = []
        for travis_section, dummy in self.travis2docker_section:
            travis2docker_section = self.get_travis_section(travis_section)
            if isinstance(travis2docker_section, types.GeneratorType):
                travis2docker_cmd_iter_list.append([
                    item_iter for item_iter in travis2docker_section
                ])
            elif isinstance(travis2docker_section, basestring):
                travis2docker_cmd_static_str += travis2docker_section + "\n"
        for combination in itertools.product(*travis2docker_cmd_iter_list):
            command_str = '\n'.join(combination) + "\n" + \
                travis2docker_cmd_static_str
            yield command_str

    def get_travis2docker(self):
        count = 1
        fname_scripts = []
        for cmd in self.get_travis2docker_iter():
            fname = os.path.join(
                self.scripts_root_path,
                str(count)
            )
            if not os.path.exists(fname):
                os.makedirs(fname)
            if self.command_format == 'bash':
                fname = os.path.join(fname, 'script.sh')
                cmd = self.get_default_cmd(os.path.dirname(fname)) + cmd
            elif self.command_format == 'docker':
                fname = os.path.join(fname, 'Dockerfile')
                cmd = self.get_default_cmd(os.path.dirname(fname)) + cmd
            with open(fname, "w") as fdockerfile:
                fdockerfile.write(cmd)
            if self.command_format == 'bash':
                st = os.stat(fname)
                os.chmod(fname, st.st_mode | stat.S_IEXEC)
            count += 1
            fname_scripts.append(fname)
        return fname_scripts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "git_repo_url",
        help="Specify repository git of work."
             "\nThis is used to clone it "
             "and get file .travis.yml or .shippable.yml",
    )
    parser.add_argument(
        "git_revision",
        help="Revision git of work."
             "\nYou can use a sha e.g. b48228"
             " or branch name e.g. master"
             " or pull number e.g. pull/1",
    )
    args = parser.parse_args()
    sha = args.git_revision
    git_repo = args.git_repo_url
    travis_obj = travis(
        git_repo,
        sha,
    )
    return travis_obj.get_travis2docker()


if __name__ == '__main__':
    FNAME_SCRIPTS = main()
    stdout.write(' '.join(FNAME_SCRIPTS) + '\n')

#!/usr/bin/python
# coding: utf-8


#       html_msg = \
#           '<div>\n<ul>\n<li>{line1}</li>\n<li>{line2}</li>\n</ul>\n</div>'
#       html_msg = html_msgline1=line1, line2=line2)
#           '<div>\n<ul>\n<li>%(line1)s</li>\n<li>%(line2)s</li>\n</ul>\n'\
#            '</div>'
#        html_msg = html_msg % ({'line1': line1, 'line2': line2})


import ast
import argparse
import os


def replace_format_by_varname(path_module):
    """Find the ) and replace them by %(varname)"""

    import pdb;pdb.set_trace()
    path_module = path_module
    files = os.listdir(path_module)
    for element in files:
        file_path = os.path.join(path_module, element)
        if os.path.isdir(file_path) and element != '__unported__':
            # os.system("find %(file_path)s -type f -name '*.py' -exec sed -i 's/.format(//g' {} \;" % ({'file_path': file_path}))
            files_found = os.listdir(file_path)


def main():
    """Method main to get args and call other methods"""

    parser = argparse.ArgumentParser()

    parser.add_argument("-p",
                        "--path",
                        metavar='PATH',
                        type=str,
                        required=True,
                        help="The path of the module in that you want to "
                        "replace ) by %(varname)",)

    args = parser.parse_args()

    path_module = args.path
    replace_format_by_varname(path_module)

if __name__ == '__main__':
    main()

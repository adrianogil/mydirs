# mydirs
Command line tool to bookmark directories.

# How to Install
Just create a macro 'MYDIRS_DIRECTORY' with the path of this project.

You can also use [gil-install][https://github.com/adrianogil/gil-tools/blob/master/src/python/gil_install.py]:
```
gil-install -i
```

# Command line options

Save current directory using <directory-alias>

```
mydirs -s <directory-alias>
```

Open directory from <directory-alias>
```
mydirs -o <directory-alias>
```

Remove direction with alias <directory-alias>
```
mydirs -d <directory-alias>
```

Show if current directory is already saved
```
mydirs -q
```

Print the path saved using <directory-alias>
```
mydirs -p <directory-alias>
```

Show history of last mydirs directory changes
```
mydirs -bh <number>
```

Go back to last mydirs directory
```
mydirs -b
```

## Planned features


## Contributing

Feel free to submit PRs. I will do my best to review and merge them if I consider them essential.

## Development status

This is a very alpha software. The code was written with no consideration of coding standards and architecture. A refactoring would do it good...

## See also

- https://github.com/huyng/bashmarks
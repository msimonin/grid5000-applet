Here we go :

![Alt text](applet.png "grid5000 applet")

### Launch it

```
python g5k-applet.py -c conf_file
```

If you are using `restfully` you can use the same config file if not, the file can be created with:

```
echo '
uri: https://api.grid5000.fr/sid/grid5000
username: MYLOGIN
password: MYPASSWORD
' > ~/.g5-applet/api.grid5000.fr.yml && chmod 600 ~/.g5k-applet/api.grid5000.fr.yml
```
### Changelog

#### version 0.1

* Periodic check (every 10 min by default)
* Refresh on demand

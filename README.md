# django-distill

`django-distill` now has a website. Read more at:

## :link: https://django-distill.com/

`django-distill` is a minimal configuration static site generator and publisher
for Django. Most Django versions are supported, however up to date versions are
advised including the Django 3.x releases. `django-distill` as of the 1.7 release
only supports Python 3. Python 2 support has been dropped. If you require Python 2
support please pin `django-distill` to version 1.6 in your requirements.txt or
Pipfile. Python 3.6 or above is advised.

`django-distill` extends existing Django sites with the ability to export
fully functional static sites. It is suitable for sites such as blogs that have
a mostly static front end but you still want to use a CMS to manage the
content.

`django-distill` iterates over URLs in your Django project using easy to write
iterable functions to yield the parameters for whatever pages you want to save
as static HTML. These static files can be automatically uploaded to a bucket-style
remote container such as Amazon S3, Googe Cloud Files, Microsoft Azure Storage,
or, written to a local directory as a fully working local static version of
your project. The site generation, or distillation process, can be easily
integrated into CI/CD workflows to auto-deploy static sites on commit.
`django-distill` can be defined as an extension to Django to make Django
projects compatible with "Jamstack"-style site architecture.

`django-distill` plugs directly into the existing Django framework without the
need to write custom renderers or other more verbose code. You can also integrate
`django-distill` with existing dynamic sites and just generate static pages for
a small subsection of pages rather than the entire site.

For static files on CDNs you can use the following 'cache buster' library to
allow for fast static media updates when pushing changes:

[:link: meeb/django-cachekiller](https://github.com/meeb/django-cachekiller)

There is a complete example site that creates a static blog and uses
`django-distill` with `django-cachekiller` via continuous deployment on Netlify
available here:

[:link: meeb/django-distill-example](https://github.com/meeb/django-distill-example)


# Installation

Install from pip:

```bash
$ pip install django-distill
```

Add `django_distill` to your `INSTALLED_APPS` in your `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps here ...
    'django_distill',
]
```

That's it.


# Limitations

`django-distill` generates static pages and therefore only views which allow
`GET` requests that return an `HTTP 200` status code are supported.

It is assumed you are using URI parameters such as `/blog/123-abc` and not
querystring parameters such as `/blog?post_id=123&title=abc`. Querystring
parameters do not make sense for static page generation for obvious reasons.

Static media files such as images and style sheets are copied from your static
media directory defined in `STATIC_ROOT`. This means that you will want to run
`./manage.py collectstatic` **before** you run `./manage.py distill-local`
if you have made changes to static media. `django-distill` doesn't chain this
request by design, however you can enable it with the `--collectstatic`
argument.


# Usage

Assuming you have an existing Django project, edit a `urls.py` to include the
`distill_path` function which replaces Django's standard `path` function and
supports the new keyword arguments `distill_func` and `distill_file`.

The `distill_func` argument should be provided with a function or callable
class that returns an iterable or `None`.

The `distill_file` argument is entirely optional and allows you to override the
URL that would otherwise be generated from the reverse of the URL regex. This
allows you to rename URLs like `/example` to any other name like
`example.html`. As of v0.8 any URIs ending in a slash `/` are automatically
modified to end in `/index.html`. You can use format string parameters in the
`distill_file` to customise the file name, arg values from the URL will be
substituted in, for example `{}` for positional args or `{param_name}` for
named args.

An example distill setup for a theoretical blogging app would be:

```python
# Replaces the standard django.conf.path, identical syntax
from django_distill import distill_path

# Views and models from a theoretical blogging app
from blog.views import PostIndex, PostView, PostYear
from blog.models import Post

def get_index():
    # The index URI path, '', contains no parameters, named or otherwise.
    # You can simply just return nothing here.
    return None

def get_all_blogposts():
    # This function needs to return an iterable of dictionaries. Dictionaries
    # are required as the URL this distill function is for has named parameters.
    # You can just export a small subset of values here if you wish to
    # limit what pages will be generated.
    for post in Post.objects.all():
        yield {'blog_id': post.id, 'blog_title': post.title}

def get_years():
    # You can also just return an iterable containing static strings if the
    # URL only has one argument and you are using positional URL parameters:
    return (2014, 2015)
    # This is really just shorthand for ((2014,), (2015,))

urlpatterns = (
    # e.g. / the blog index
    distill_path('',
                 PostIndex.as_view(),
                 name='blog-index',
                 # Note that for paths which have no paramters
                 # distill_func is optional
                 distill_func=get_index,
                 # '' is not a valid file name! override it to index.html
                 distill_file='index.html'),
    # e.g. /post/123-some-post-title using named parameters
    distill_path('post/<int:blog_id>-<slug:blog_title>.html',
                 PostView.as_view(),
                 name='blog-post',
                 distill_func=get_all_blogposts),
    # e.g. /posts-by-year/2015 using positional parameters
    # url ends in / so file path will have /index.html appended
    distill_path('posts-by-year/<int:year>/',
                 PostYear.as_view(),
                 name='blog-year',
                 distill_func=get_years),
)
```

Your site will still function identically with the above changes. Internally
the `distill_func` and `distill_file` parameters are removed and the URL is
passed back to Django for normal processing. This has no runtime performance
impact as this happens only once upon starting the application.

If your path has no URI paramters, such as `/` or `/some-static-url` you do
not have to specify the `distill_func` parameter if you don't want to. As for
paths with no parameters the `distill_func` always returns `None`, this is set
as the default behaviour for `distill_func`s.

You can use the `distill_re_path` function as well, which replaces the default
`django.urls.re_path` function. Its usage is identical to the above:

```python
from django_distill import distill_re_path

urlpatterns = (
    distill_re_path(r'some/regex'
                    SomeOtherView.as_view(),
                    name='url-other-view',
                    distill_func=some_other_func),
)

```

If you are using an older version of Django in the 1.x series you can use the
`distill_url` function instead which replaces the `django.conf.urls.url` or
`django.urls.url` functions. Its usage is identical to the above:

```python
from django_distill import distill_url

urlpatterns = (
    distill_url(r'some/regex'
                SomeView.as_view(),
                name='url-view',
                distill_func=some_func),
)
```

### Parameters in file names

You can use standard Python string formatting in `distill_file` as well to enable
you to change the output file path for a file if you wish. Note this does not
update the URL used by Django so if you use this make sure your `path` pattern
matches the `distill_file` pattern or your links might not work in Django. An
example:

```python
# Override file path with parameters. Values are taken from the URL pattern
urlpatterns = (
    distill_path('post/<int:blog_id>-<slug:blog_title>.html',
                 PostView.as_view(),
                 name='blog-post',
                 distill_func=get_all_blogposts,
                 distill_file="post/{blog_id}-{blog_title}.html"
)
```

### Non-standard status codes

All views rendered by `django-distill` into static pages must return an HTTP 200 status
code. If for any reason you need to render a view which does not return an HTTP 200
status code, for example you also want to statically generate a 404 page which has a
view which (correctly) returns an HTTP 404 status code you can use the
`distill_status_codes` optional argument to a view. For example:

```python
from django_distill import distill_url

urlpatterns = (
    distill_url(r'some/regex'
                SomeView.as_view(),
                name='url-view',
                distill_status_codes=(200, 404),
                distill_func=some_func),
)
```

The optional `distill_status_codes` argument accepts a tuple of status codes as integers
which are permitted for the view to return without raising an error. By default this is
set to `(200,)` but you can override it if you need to for your site.

### Tracking Django's URL function support

`django-distill` will mirror whatever your installed version of Django supports,
therefore at some point the `distill_url` function will cease working in the future
when Django 2.x itself depreciates the `django.conf.urls.url` and `django.urls.url`
functions. You can use `distill_re_path` as a drop-in replacement. It is advisable to
use `distill_path` or `distill_re_path` if you're building a new site now.


### Internationalization

Internationalization is only supported for URLs, page content is unable to be
dynamically translated. By default your site will be generated using the
`LANGUAGE_CODE` value in your `settings.py`. If you also set `settings.USE_I18N` to
`True` then set other language codes in your `settings.DISTILL_LANGUAGES` value and register
URLs with `i18n_patterns(...)` then your site will be generated in multiple languges.
This assumes your multi-language site works as expected before adding `django-distill`.

For example if you set `settings.LANGUAGE_CODE = 'en'` your site will be
generated in one language.

If you have something like this in your `settings.py` instead:

```python
USE_I18N = True

DISTILL_LANGUAGES = [
    'en',
    'fr',
    'de',
]
```

While also using `i18n_patterns`in your `urls.py` like so:

```python
from django.conf.urls.i18n import i18n_patterns
from django_distill import distill_path

urlpatterns = i18n_patterns(
    distill_path('some-file.html',
                 SomeView.as_view(),
                 name='i18n-view',
                 distill_func=some_func
    )
)
```

Then your views will be generaged as `/en/some-file.html`, `/fr/some-file.html`
and `/de/some-file.html`. These URLs should work (and be translated) by your
site already. `django-distill` doesn't do any translation magic, it just
calls the URLs with the language code prefix.

**Note** While the default suggested method is to use `settings.DISTILL_LANGUAGES`
to keep things seperate `django-distill` will also check `settings.LANGUAGES` for
language codes.


### Sitemaps

You may need to generate a list of all the URLs registered with `django-distill`.
For example, you have a statically generated blog with a few hundred pages and
you want to list all of the URLs easily in a `sitemap.xml` or other similar list
of all URLs. You could wrap your sitemap view in `distill_path` then replicate
all of your URL generation logic by importing your views `distill_func`s from
your `urls.py` and generating these all manually, but given this is quite a hassle
there's a built-in helper to generate all your URLs that will be distilled for you.

```python
from django_distill import distilled_urls

for uri, file_name in distilled_urls():
    # URI is the generated, complete URI for the page
    print(uri)        # for example: /blog/my-post-123/
    # file_name is the actual file name on disk, this may be None or a string
    print(file_name)  # for example: /blog/my-post-123/index.html
```

**Note** that `distilled_urls()` will only return URLs after all of your URLs
in `urls.py` have been loaded with `distill_path(...)`.


# The `distill-local` command

Once you have wrapped the URLs you want to generate statically you can now
generate a complete functioning static site with:

```bash
$ ./manage.py distill-local [optional /path/to/export/directory]
```

Under the hood this simply iterates all URLs registered with `distill_url` and
generates the pages for them using parts of the Django testing framework to
spoof requests. Once the site pages have been rendered then files from the
`STATIC_ROOT` are copied over. Existing files with the same name are replaced in
the target directory and orphan files are deleted.

`distill-local` supports the following optional arguments:

`--collectstatic`: Automatically run `collectstatic` on your site before
rendering, this is just a shortcut to save you typing an extra command.

`--quiet`: Disable all output other than asking confirmation questions.

`--force`: Assume 'yes' to all confirmation questions.

`--exclude-staticfiles`: Do not copy any static files at all, only render output from
Django views.

`--parallel-render [number of threads]`: Render files in parallel on multiple
threads, this can speed up rendering. Defaults to `1` thread.

`--generate-redirects`: Attempt to generate static redirects stored in the
`django.contrib.redirects` app. If you have a redirect from `/old/` to `/new/` using
this flag will create a static HTML `<meta http-equiv="refresh" content="...">`
style redirect at `/old/index.html` to `/new/`.

**Note** If any of your views contain a Python error then rendering will fail
then the stack trace will be printed to the terminal and the rendering command
will exit with a status code of 1.


# The `distill-publish` command

```bash
$ ./manage.py distill-publish [optional destination here]
```

If you have configured at least one publishing destination (see below) you can
use the `distill-publish` command to publish the site to a remote location.

This will perform a full synchronisation, removing any remote files that are no
longer present in the generated static site and uploading any new or changed
files. The site will be built into a temporary directory locally first when
publishing which is deleted once the site has been published. Each file will be
checked that it has been published correctly by requesting it via the
`PUBLIC_URL`.

`distill-publish` supports the following optional arguments:

`--collectstatic`: Automatically run `collectstatic` on your site before
rendering, this is just a shortcut to save you typing an extra command.

`--quiet`: Disable all output other than asking confirmation questions.

`--force`: Assume 'yes' to all confirmation questions.

`--exclude-staticfiles`: Do not copy any static files at all, only render output from
Django views.

`--skip-verify`: Do not test if files are correctly uploaded on the server.

`--ignore-remote-content`: Do not fetch the list of remote files. It means that all
files will be uploaded, and no existing remote file will be  deleted. This can be
useful if you have a lot of files on the remote server, and you know that you want
to update most of them, and you don't care if old files remain on the server.

`--parallel-publish [number of threads]`: Publish files in parallel on multiple
threads, this can speed up publishing. Defaults to `1` thread.

`--parallel-render [number of threads]`: Render files in parallel on multiple
threads, this can speed up rendering. Defaults to `1` thread.

`--generate-redirects`: Attempt to generate static redirects stored in the
`django.contrib.redirects` app. If you have a redirect from `/old/` to `/new/` using
this flag will create a static HTML `<meta http-equiv="refresh" content="...">`
style redirect at `/old/index.html` to `/new/`.

**Note** that this means if you use `--force` and `--quiet` that the output
directory will have all files not part of the site export deleted without any
confirmation.

**Note**  If any of your views contain a Python error then rendering will fail
then the stack trace will be printed to the terminal and the rendering command
will exit with a status code of 1.


# The `distill-test-publish` command

```bash
$ ./manage.py distill-test-publish [optional destination here]
```

This will connect to your publishing target, authenticate to it, upload a
randomly named file, verify it exists on the `PUBLIC_URL` and then delete it
again. Use this to check your publishing settings are correct.

`distill-test-publish` has no arguments.


# Optional configuration settings

You can set the following optional `settings.py` variables:

**DISTILL_DIR**: string, default directory to export to:

```python
DISTILL_DIR = '/path/to/export/directory'
```

**DISTILL_PUBLISH**: dictionary, like Django's `settings.DATABASES`, supports
`default`:

```python
DISTILL_PUBLISH = {
    'default': {
        ... options ...
    },
    'some-other-target': {
        ... options ...
    },
}
```

**DISTILL_SKIP_ADMIN_DIRS**: bool, defaults to `True`

```python
DISTILL_SKIP_ADMIN_DIRS = True
```

Set `DISTILL_SKIP_ADMIN_DIRS` to `False` if you want `django-distill` to also copy over
static files in the `static/admin` directory. Usually, these are not required or
desired for statically generated sites. The default behaviour is to skip static admin
files.


**DISTILL_SKIP_STATICFILES_DIRS**: list, defaults to `[]`

```python
DISTILL_SKIP_STATICFILES_DIRS = ['some_dir']
```

Set `DISTILL_SKIP_STATICFILES_DIRS` to a list of directory names you want `django-distill`
to ignore directories in your defined `static/` directory. You can use this to ignore
copying directories containing files from apps you're not using that get bundled into your
`static/` directory by `collect-static`. For example if you set `DISTILL_SKIP_STATICFILES_DIRS`
to `['some_dir']` the static files directory `static/some_dir` would be skipped.


**DISTILL_LANGUAGES**: list, defaults to `[]`

```python
DISTILL_LANGUAGES = [
    'en',
    'fr',
    'de',
]
```

Set `DISTILL_LANGUAGES` to a list of language codes to attempt to render URLs with.
See the "Internationalization" section for more details.


# Developing locally with HTTPS

If you are using a local development environment which has HTTPS support you may need
to add `SECURE_SSL_REDIRECT = False` to your `settings.py` to prevent a `CommandError`
being raised when a request returns a 301 redirect instead of the expected HTTP/200
response code.


# Writing single files

As of `django-distill` version `3.0.0` you can use the
`django_distill.renderer.render_single_file` method to write out a single file
to disk using `django_distill`. This is useful for writing out single files to disk,
for example, you have a Django site which has some static files in a directory
written by `django_distill` but the rest of the site is a normal dynamic Django site.
You can update a static HTML file every time a model instance is saved. You can
use single file writing with signals to achieve this. For example:

```python
# in models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_distill.renderer import render_single_file

@receiver(post_save, sender=SomeBlogPostModel)
def write_blog_post_static_file_post_save(sender, **kwargs):
    render_single_file(
        '/path/to/output/directory',
        'blog-post-view-name',
        blog_id=sender.pk,
        blog_slug=sender.slug
    )
```

The syntax for `render_single_file` is similar to Django's `url.reverse`. The full
usage interface is:

```python
render_single_file(
    '/path/to/output/directory',
    'view-name-set-in-urls-py',
    *view_args,
    **view_kwargs
)
```

For example, if you had a blog post URL defined as:

```python
    # in urls.py
    distill_path('post/<int:blog_id>_<slug:blog_slug>.html',
                 PostView.as_view(),
                 name='blog-post',
                 distill_func=get_all_blogposts),
```

Your usage would be:

```python
render_single_file(
    '/path/to/output/directory',
    'blog-post',
    blog_id=123,
    blog_slug='blog-title-slug',
)
```

which would write out the contents of `/post/123_blog-title-slug.html` into
`/path/to/output/directory` as the file
`/path/to/output/directory/post/123_blog-title-slug.html`. Note any required
sub-directories (`/path/to/output/directory/post` in this example) will be
automatically created if they don't already exist. All `django-distill` rules
apply, such as URLs ending in `/` will be saved as `/index.html` to make sense
for a physical file on disk.

Also note that `render_single_file` can only be imported and used into an
initialised Django project.


# Publishing targets

You can automatically publish sites to various supported remote targets through
backends just like how you can use MySQL, SQLite, PostgreSQL etc. with
Django by changing the backend database engine. Currently the engines supported
by `django-distill` are:

**django_distill.backends.amazon_s3**: Publish to an Amazon S3 bucket. Requires
  the Python library `boto3` (`$ pip install django-distill[amazon]`). The bucket
  must already exist (use the AWS control panel). Options:

```python
'some-s3-container': {
    'ENGINE': 'django_distill.backends.amazon_s3',
    'PUBLIC_URL': 'http://.../',
    'ACCESS_KEY_ID': '...',
    'SECRET_ACCESS_KEY': '...',
    'BUCKET': '...',
    'ENDPOINT_URL': 'https://.../',  # Optional, set to use a different S3 endpoint
    'DEFAULT_CONTENT_TYPE': 'application/octet-stream',  # Optional
},
```

**django_distill.backends.google_storage**: Publish to a Google Cloud Storage
  bucket. Requires the Python libraries `google-api-python-client` and
  `google-cloud-storage`
  (`$ pip install django-distill[google]`). The bucket
  must already exist and be set up to host a public static website (use the
  Google Cloud control panel). Options:

```python
'some-google-storage-bucket': {
    'ENGINE': 'django_distill.backends.google_storage',
    'PUBLIC_URL': 'https://storage.googleapis.com/[bucket.name.here]/',
    'BUCKET': '[bucket.name.here]',
    'JSON_CREDENTIALS': '/path/to/some/credentials.json',
},
```

Note that `JSON_CREDENTIALS` is optional; if it is not specified, the google libraries
will try other authentication methods, in the search order described here:
https://cloud.google.com/docs/authentication/application-default-credentials (e.g. the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable, attached service account, etc).


**django_distill.backends.microsoft_azure_storage**: Publish to a Microsoft
  Azure Blob Storage container. Requires the Python library
  `azure-storage-blob` (`$ pip install django-distill[microsoft]`). The storage
  account must already exist and be set up to host a public static website
  (use the Microsoft Azure control panel). Options:

```python
'some-microsoft-storage-account': {
    'ENGINE': 'django_distill.backends.microsoft_azure_storage',
    'PUBLIC_URL': 'https://[storage-account-name]...windows.net/',
    'CONNECTION_STRING': '...',
},
```

Note that each Azure storage account supports one static website using the
magic container `$web` which is where `django-distill` will attempt to
publish your site.


# Tests

There is a minimal test suite, you can run it by cloing this repository,
installing the required dependancies in `requirements.txt` then execuiting:

```bash
# ./run-tests.py
```


# Contributing

All properly formatted and sensible pull requests, issues and comments are
welcome.

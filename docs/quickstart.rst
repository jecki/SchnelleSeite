SchnelleSeite - Quickstart
==========================

Installation
------------

This section is coming soon...


Starting a new project
----------------------

In order to start a new site with *SchnelleSeite* simply type [#fn1]_ ::

  $ python3 SchnelleSeite.py --init ~/newsite

in a shell window. *SchnelleSeite* will then create a new directory
``newsite`` in your home directory and initialize it with a simple
default project. Of course, you can use any other directory path
instead of ``~/newsite``. Then type: ::

  $ python3 SchnelleSeite.py ~/newsite

This will build your new static website. The static site will be
stored a newly created ``__site`` sub-directory of your project
directory. *SchnelleSeite* will automatically start a web-browser and
show the new site after building.

As you can see the scaffold site contains two pages, an index or main
page and an info or about page. Both of these pages exist in an
English as well as a German version. No matter what page you are on,
you can always switch to another language version of the same page by
clicking on the respective language link.

The languages that your project supports are configured in the
``__site-config.yaml`` file in the main directory of your project. In
*SchnelleSeite* all pages (or :ref:`page fragments`) are assumed to
exist versions for every language of your project. Should some
resource not be present in a particular language version, then
*SchnelleSeite* will fallback to a different language. [#fn2]_


Adding content
--------------

Now let's add some content to your website. Say, you want to change
the content of the main page. The main page is
``index.html``. However, in the scaffold site, ``index.html`` is just
a template that adds its context from the folder ``_index``. (Have a
look at the source code of ``index.html`` if you would like to know
how this works. You need to know html and jinja templates to
understand the source.) In the index folder you find one file named
``content.md``. The file extension ``.md`` stands for `markdown`_,
which is a strongly simplified markup language for web content - much
simpler and more readable than html, though not nearly as powerful. If
you open this file in a text editor, it will look something like
this::

  +++
  language: DE
  +++
  # SchnelleSeite. Ein statischer Seitengenerator 

  *SchnelleSeite* ist ein statischer Seitengenerator, mit besonderer
  Unterstützung für mehrsprachige Websites.

  Viel Spaß damit!

  +++
  language: EN
  +++
  # SchnelleSeite. A static site generator

  *SchnelleSeite* is a static site generator with special support for 
  multilingual web sites.
  
  Enjoy!

As you can see, both language versions of the page content are
contained in the same file. Each language version starts with a
meta-data block that is enclosed by ``+++``-lines. Meta-data must
always be in the `yaml`_-format, which is a simple and very human
readable markup language for data. The meta-data block that introduces
a new language version must define a ``language``-variable, the value
of which is a two letter (e.g. "EN") or five letter (e.g. "en_US")
language code. The meta-data block may also contain further variables,
which are then specific for that language version of the
content. After the meta-data block follows the content, which you are
now free to change at liberty. After you have made some changes, rerun
``python3 SchnelleSeite.py ~/home/newsite`` to see the updated static
site. The new content should appear at its proper place.

It is by now means necessary to place the all language versions in one
and the same file as done here. This is just one of several options
that *SchnelleSeite* offers to organize your content. If the texts are
not too long, I find it more practical to keep different language
versions in one file rather than to distribute them over different
files.

.. _markdown: http://markdown???
.. _yaml: http://yaml


Organisation of the project folder
----------------------------------

coming soon...

Structure of the site
---------------------

coming soon...


.. rubric:: Footnotes

.. [#fn1] *SchnelleSeite* requires Python 3.2 or higher. Depending on
	your system configuration it suffices to type ``python``
	instead of ``python3``.
	
.. [#fn2] As of version 0.1, English is hardcoded as the default
        fallback language. In case no English version is present an
        arbitrary language version is picked. The fallback order will
        be made configurable in the future.

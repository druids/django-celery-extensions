.. highlight:: shell

============
Installation
============

Library purpose
---------------

Library extends celery framework with these improvements:
* Automatic Django commands conversion to the celery tasks
* Improve celery signals with on apply, trigger, unique or timeout events
* Add possibility to create the unique celery task
* Add possibility to ignore task invocation for the defined timeout
* Fix some celery bugs with the expiration
* Better AWS SQS support
* Apply a task and wait for the result for the timeout
* Celery beater implementation which will ensure that only one beater can be active if more beater are running at the same time
* Define celery queues in the enums
* Use Django checks to validate celery tasks settings

Stable release
--------------

To install Django celery extensions, run this command in your terminal:

.. code-block:: console

    $ pip install django-celery-extensions

This is the preferred method of installation, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/druids/django-celery-extensions

Or download the `tarball`_:

.. code-block:: console

    $ curl -OL https://github.com/druids/django-celery-extensions/tarball/master

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ make install


.. _Github repo: https://github.com/druids/django-celery-extensions
.. _tarball: https://github.com/druids/django-celery-extensions/tarball/master


Enable the library
------------------

Once installed, add the library to ``INSTALLED_APPS`` in your Django project settings::

    INSTALLED_APPS = [
        ...
        'django_celery_extensions',
        ...
    ]

For your celery configuration use ``django_celery_extensions.celery.Celery`` class::

    from django_celery_extensions.celery import Celery

    app = Celery('example')

You can use ``django_celery_extensions.celery.CeleryQueueEnum`` to define default configuration for tasks in the queue::


    from django_celery_extensions.celery import CeleryQueueEnum

    class CeleryQueue(CeleryQueueEnum):
        FAST = ('fast', {'time_limit': 10})


You can define task and set the right queue now::

    @celery_app.task(queue=CeleryQueue.FAST)
    def task_with_fast_queue():
        return 'result'

If you need to override celery task class you should use ``django_celery_extensions.task.DjangoTask`` class::


    from django_celery_extensions.task import DjangoTask

    class YourTask(DjangoTask):
        ...

    @celery_app.task(base=YourTask)
    def your_task():
        return 'result'

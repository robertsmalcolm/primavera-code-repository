.. gridsmoother documentation master file, created by
   sphinx-quickstart on Thu May  7 10:10:47 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to gridsmoother's documentation!
========================================

Contents:


.. toctree::
   :maxdepth: 1

   gridsmoother.rst

The :py:class:`GridSmoother` class is designed to smooth latitude-longitude fields with a true spatial smoothing function rather than a function of grid index (noting that grid cells become much smaller close to the poles).

For example the following image shows an N48 field smoothed with a 10 degree radial cap function (i.e. smoothing function returns 1 for angular separations less than or equal to 10).

.. image:: _static/example.png

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


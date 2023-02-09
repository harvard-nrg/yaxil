.. _xnat_auth:

xnat_auth: authentication setup with verification
===================================================
The ``xnat_auth`` command line tool will assist you with creating a ``~/.xnat_auth`` file. Here's an example invocation of the ``xnat_auth`` tool

.. code-block:: bash
  
  xnat_auth --alias cbscentral --url https://cbscentral.rc.fas.harvard.edu --username MJbball1991

The tool will prompt you for your XNAT password. If the username and password cannot be used to authenticate to the provided ``--url``, the script will return an error and you'll need to rerun it.

The output file ``~/.xnat_auth`` should look like so

.. code-block:: xml
 
  <xnat>
    <cbscentral version="1.5">
      <url>https://cbscentral.rc.fas.harvard.edu</url>
      <username>MJbball1991</username>
      <password>DaBullsDaBullsDaBullsDaBulls</password>
    </cbscentral>
  </xnat>

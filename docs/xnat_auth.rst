.. _xnat_auth

xnat_auth: authentication setup with verification
===================================================

-----------------------------------------

This tool is completely optional to use. You are free to simply edit the ``~/.xnat_auth``
file directly using your text editor of choice, and the following template:

.. code-block:: xml
 
  <xnat>
      <cbscentral version="1.5">
      <url>https://cbscentral.rc.fas.harvard.edu</url>
      <username>MJbball1991</username>
      <password>DaBullsDaBullsDaBullsDaBulls</password>
      </cbscentral>
  </xnat>

Basic Usage
-----------
If you want to download all scans for a MR Session, just use this command, and enter your password when prompted:

.. code-block:: bash
  
  xnat_auth --alias cbscentral --url https://cbscentral.rc.fas.harvard.edu --username MJbball1991

If your username/password combination cannot be used to authenticate to your URL, the script will return an error and you will need to rerun it.

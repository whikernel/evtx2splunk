import setuptools


setuptools.setup(
     name='evtx2splunk',
     version='2.0.1',
     packages=['evtx2splunk', 'evtx2splunk.evtxdump'],
     author="whitekernel - PAM",
     description="Ingest EVTX files into a Splunk instance.",
     url="https://github.com/whikernel/evtx2splunk",
     classifiers=[
         "Programming Language :: Python :: 3",
         "License :: OSI Approved :: MIT",
         "Operating System :: OS Independent",
     ]
 )

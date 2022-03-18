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
     ],
    install_requires=[
        'certifi==2021.10.8',
        'chardet==4.0.0',
        'idna==3.3',
        'python-dotenv == 0.15.0',
        'requests==2.26.0',
        'semantic-version == 2.8.5',
        'urllib3>=1.26.5',
        'toml==0.10.2',
        'tqdm==4.59.0',
        'splunk-hec @ git+https://github.com/georgestarcher/Splunk-Class-httpevent.git'
    ]

 )

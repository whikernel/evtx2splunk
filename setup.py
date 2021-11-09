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
        'certifi==2020.12.5',
        'chardet==4.0.0',
        'idna==2.10',
        'python-dotenv == 0.15.0',
        'requests==2.25.1',
        'semantic-version == 2.8.5',
        'urllib3>=1.26.5',
        'toml==0.10.2',
        'tqdm==4.59.0',
        'setuptools~=46.1.3',
        'splunk-hec @ git+https://github.com/georgestarcher/Splunk-Class-httpevent.git'
    ]

 )

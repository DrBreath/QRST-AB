from setuptools import setup, find_packages

setup(
    name='qrst',  # 包名，与 pip install 中的名称相同
    version='0.1.0',  # 版本号
    author='DrBreath',
    author_email='cli@doclive.cn',
    description='QRST-AB or QRST is a  QR code-based secure transmission algorithm (QRST-AB) using Avro and Byte Pair Encoding (BPE)',
    long_description=open('README.md').read(),  # 从 README.md 读取长描述
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/qrst',  # 项目的 URL
    packages=find_packages(),  # 自动找到包
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',  # Python 版本要求
    install_requires=[
        'numpy',
        'sentencepiece',
        'avro'
    ],
)
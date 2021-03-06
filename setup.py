from setuptools import setup


def parse_requirements(filename):
    """ load requirements from a pip requirements file """
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not
            line.startswith("#")]


install_reqs = parse_requirements('./requirements.txt')
reqs = [str(ir) for ir in install_reqs]

setup(name='torch_itl',
      version='0.1dev',
      description='pytorch compatible integral loss minimization',
      author='Alex Lambert',
      author_email='alex.lambert@protonmail.com',
      license='MIT',
      packages=['torch_itl', 'torch_itl.estimator', 'torch_itl.kernel',
                'torch_itl.model', 'torch_itl.sampler', 'torch_itl.datasets'],
      include_package_data=True,
      install_requires=reqs,
      zip_safe=False)

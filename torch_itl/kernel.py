import torch

dtype = torch.float
device = torch.device("cpu")


def rbf_kernel(X, Y=None, gamma=None):
    """Compute rbf Gram matrix between X and Y (or X)
    Parameters
    ----------
    X: torch.Tensor of shape (n_samples_1, n_features)
       First input on which Gram matrix is computed
    Y: torch.Tensor of shape (n_samples_2, n_features), default None
       Second input on which Gram matrix is computed. X is reused if None
    gamma: float
           Gamma parameter of the kernel (see sklearn implementation)
    Returns
    -------
    K: torch.Tensor of shape (n_samples_1, n_samples_2)
       Gram matrix on X/Y
    """
    if Y is None:
        Y = X

    if gamma is None:
        gamma = 1.0 / X.shape[1]

    X_norm = (X ** 2).sum(1).view(-1, 1)
    Y_norm = (Y ** 2).sum(1).view(1, -1)
    K_tmp = X_norm + Y_norm - 2. * torch.mm(X, torch.t(Y))
    K_tmp *= -gamma
    K = torch.exp(K_tmp)

    return K

class Kernel(object):

    def __init__(self):
        pass

class Gaussian(Kernel):

    def __init__(self, gamma):
        self.gamma = gamma
        self.is_learnable = False

    def compute_gram(self,X,Y=None):
        return rbf_kernel(X,Y,self.gamma)

class Learnable_gaussian(Kernel):

    def __init__(self, gamma, model, optim_params):
        self.gamma= gamma
        self.is_learnable = True
        self.model = model
        self.optim_params = optim_params

    def compute_gram(self,X,Y=None):
        if Y is None:
            return rbf_kernel(self.model.forward(X))
        else:
            return rbf_kernel(self.model.forward(X),self.model.forward(Y))

    def regularization(self):
        return 0

    def clear_memory(self):
        self.losses, self.times = [], [0]

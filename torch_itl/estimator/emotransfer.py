import torch
from .vitl import VITL
from .utils import squared_norm
from scipy.linalg import solve_sylvester


class EmoTransfer(VITL):
    """Implements emotion transfer with squared loss as proposed in
    'Emotion Transfer Using Vector-Valued Infinite Task Learning'
    """

    def __init__(self, model, lbda, sampler, input_type, inc_emotion=True):
        super().__init__(model, squared_norm, lbda, sampler)
        self.input_type = input_type
        self.inc_emotion = inc_emotion

    def initialise(self, data):
        """
        Transforms data into suitable x_train, y_train for which
        the Ridge Regression is performed, set emotion anchors,
        and load it into the model
        Parameters
        ----------
        data: torch.Tensor of shape (n_samples, n_emotions, n_landmarks)
           Input vector of data
        Returns
        -------
        Nothing
        """
        n, m, nf = data.shape

        if self.input_type == 'joint':
            x_train = data.reshape(-1, nf)
            y_train = torch.zeros(m * n, m, nf)
            for i in range(m * n):
                y_train[i] = data[i // m]
            thetas = self.sampler.sample()
            self.model.m = m

        else:
            x_train = data[:, self.input_type, :]
            if self.inc_emotion:
                y_train = data
                thetas = self.sampler.sample()
                self.model.m = m
            else:
                mask = [i != input_type for i in range(m)]
                y_train = data[:, mask, :]
                thetas = self.sampler.sample()[mask]
                self.model.m = m-1

        self.model.thetas = thetas
        self.model.n = x_train.shape[0]
        self.model.x_train = x_train
        self.model.y_train = y_train

    def risk(self, data, thetas=None):
        """
        Computes the risk associated to the data
        Parameters
        ----------
        data: torch.Tensor of shape (n_samples, n_emotions, n_landmarks)
            Input vector of data
        Returns
        -------
        res: torch.Tensor of shape (1)
            risk of the predictor on the data
        """
        n, m, nf = data.shape
        if self.input_type == 'joint':
            x = data.reshape(-1, nf)
            y = torch.zeros(m * n, m, nf)
            for i in range(m * n):
                y[i] = data[i // m]

        else:
            x = data[:, self.input_type, :]
            if self.inc_emotion:
                y = data
            else:
                mask = [i != input_type for i in range(m)]
                y = data[:, mask, :]

        if thetas is None:
            thetas = self.model.thetas

        pred = self.model.forward(x, thetas)
        res = self.cost(y, pred, thetas)
        return res

    def training_risk(self):
        """
        Computes the risk associated to the stored training data
        Parameters
        ----------
        None
        Returns
        -------
        res: torch.Tensor of shape (1)
            risk of the predictor on the data
        """
        if not hasattr(self.model, 'x_train'):
            raise Exception('No training data provided')
        pred = self.model.forward(self.model.x_train, self.model.thetas)
        res = self.cost(self.model.y_train, pred, self.model.thetas)
        return res

    def fit(self, data, verbose=False):
        """
        Fits the emotion transfer model by a closed form solution
        The matrix A of the model has to be invertible
        Parameters
        ----------
        data: torch.Tensor of shape (n_samples, n_emotions, n_landmarks)
            Input vector of data
        verbose: Bool
            final print of the empirical risk (or not)
        Returns
        -------
        Nothing
        """
        if verbose:
            print('Initialize data')
        self.initialise(data)
        self.model.compute_gram_train()

        if verbose:
            print('Solving the linear system')

        if torch.norm(self.model.A - torch.eye(self.model.output_dim)) < 1e-10:
            tmp = self.model.G_xt + self.lbda * \
                self.model.n * self.model.m * \
                torch.eye(self.model.n * self.model.m)
            alpha, _ = torch.solve(
                self.model.y_train.reshape(-1, self.model.output_dim), tmp)
            self.model.alpha = alpha.reshape(self.model.n, self.model.m, -1)

        else:
            B = torch.inverse(self.model.A).numpy()
            Q = (self.model.y_train.reshape(-1, self.model.output_dim)).numpy() @ B
            alpha_np = solve_sylvester(self.model.G_xt,
                                       self.lbda * self.model.n * self.model.m * B,
                                       Q)
            self.model.alpha = torch.from_numpy(
                alpha_np).reshape(self.model.n, self.model.m, -1)

        if verbose:
            print('Coefficients alpha fitted, empirical risk=',
                  self.training_risk())

    def fit_partial(self, data, mask, verbose=False):
        """
        Fits the emotion transfer model by a closed form solution
        with missing data encoded in mask
        Parameters
        ----------
        data: torch.Tensor of shape (n_samples, n_emotions, n_landmarks)
           Input vector of data
        mask: torch.Tensor(dtype=torch.bool) of shape (n_samples, n_emotions)
        Returns
        -------
        Nothing
        """
        pass

    def fit_dim_red(self, data, s):
        """
        Fits the emotion transfer model by a closed form solution
        with low rank matrix A based on SVD of the data covariance
        ONLY SUPPORTS eigenvalues(A)=1 for now
        Parameters
        ----------
        data: torch.Tensor of shape (n_samples, n_emotions, n_landmarks)
           Input vector of data
        s: Int
            Rank of A
        Returns
        -------
        Nothing
        """
        self.initialise(data)
        self.model.compute_gram_train()

        cor = 1/self.model.n * self.model.y_train.T @ self.model.y_train
        u, d, v = torch.svd(cor)
        
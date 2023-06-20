from tqdm import trange
from sklearn import linear_model,preprocessing
import numpy as np

from scipy.stats import chi2, linregress
from sklearn.preprocessing import normalize


def llr_poisson(y, xcoords=None, exposure=None):
    s0, i0 = poisson_regression(y, xcoords=0*xcoords, exposure=exposure)
    s1, i1 = poisson_regression(y, xcoords=xcoords, exposure=exposure)
    
    ll0=poisson_likelihood(s0,i0,y,xcoords=xcoords,exposure=exposure)
    ll1=poisson_likelihood(s1,i1,y,xcoords=xcoords,exposure=exposure)
    
    return s0, i0, s1, i1, chi2.sf(2*(ll1-ll0),1)

def poisson_likelihood(slope, intercept, y, xcoords=None, exposure=None):
    lam=exposure * np.exp(slope * xcoords + intercept)
    return np.sum(y * np.log(lam) - lam)

def poisson_regression(y, xcoords=None, exposure=None, alpha=0):
    # run poisson fit on pooled data and return slope, intercept
    clf = linear_model.PoissonRegressor(fit_intercept=True,alpha=alpha,max_iter=500,tol=1e-10)
    clf.fit(np.reshape(xcoords,(-1,1)),y/exposure, sample_weight=exposure)

    return [clf.coef_[0], clf.intercept_ ]

def segmented_poisson_regression(count, totalumi, dp_labels, depth, num_layers,
                                 opt_function=poisson_regression):
    """ Fit Poisson regression per gene per layer.
    :param count: UMI count matrix of SRT gene expression, G genes by n spots
    :type count: np.array
    :param totalumi: Total UMI count per spot, a vector of n spots.
    :type totalumi: np.array
    :param dp_labels: Layer labels obtained by DP, a vector of n spots.
    :type dp_labels: np.array
    :param depth: Inferred layer depth, vector of n spots
    :type depth: np.array
    :return: A dataframe for the offset and slope of piecewise linear expression function, size of G genes by 2*L layers.
    :rtype: pd.DataFrame
    """

    G, N = count.shape
    unique_layers = np.sort(np.unique(dp_labels))
    # L = len(unique_layers)
    L=num_layers

    slope1_matrix=np.zeros((G,L))
    intercept1_matrix=np.zeros((G,L))
    
    # null setting
    slope0_matrix=np.zeros((G,L))
    intercept0_matrix=np.zeros((G,L))
    
    pval_matrix=np.zeros((G,L))

    for g in trange(G):
        for t in unique_layers:
            pts_t=np.where(dp_labels==t)[0]
            t=int(t)
            
            # need to be enough points in layer
            if len(pts_t) > 10:
                s0, i0, s1, i1, pval = llr_poisson(count[g,pts_t], xcoords=depth[pts_t], exposure=totalumi[pts_t])
            else:
                s0=np.Inf
                i0=np.Inf
                s1=np.Inf
                i1=np.Inf
                pval=np.Inf
        
            slope0_matrix[g,t]=s0
            intercept0_matrix[g,t]=i0
            
            slope1_matrix[g,t]=s1
            intercept1_matrix[g,t]=i1
            
            pval_matrix[g,t]=pval
            
    return slope0_matrix,intercept0_matrix,slope1_matrix,intercept1_matrix, pval_matrix

def get_discont_mat(s_mat, i_mat, belayer_labels, belayer_depth, num_layers):
    G,_=s_mat.shape
    L=num_layers
    discont_mat=np.zeros((G,L-1))
    
    for l in range(L-1):
        pts_l=np.where(belayer_labels==l)[0]
        pts_l1=np.where(belayer_labels==l+1)[0]
        
        if len(pts_l) > 0 and len(pts_l1) > 0:
            x_left=np.max(belayer_depth[pts_l])
            y_left=s_mat[:,l]*x_left + i_mat[:,l]

            x_right=np.min(belayer_depth[pts_l1])
            y_right=s_mat[:,l+1]*x_right + i_mat[:,l+1]
            discont_mat[:,l]=y_right-y_left
        else:
            discont_mat[:,l]=0
    return discont_mat

######################


# INPUTS:
# counts_mat: G x N matrix of counts
# belayer_labels, belayer_depth: N x 1 array with labels/depth for each spot (labels=0, ..., L-1)
# cell_type_df: N x C dataframe, rows are spots, columns are cell types, entries are cell type proportion in spot
# ct_list: list of cell types to compute piecewise linear fits for

# num_bins: number of bins to bin depth into (for visualization)
# pseudocount: pseudocount to add to counts
# umi_threshold: restrict to genes with total UMI count across all spots > umi_threshold
# after filtering, there are G' genes
# t: p-value threshold for LLR test (slope = 0 vs slope != 0)

# OUTPUTS:
# pw_fit_dict: dictionary indexed by cell types, as well as 'all_cell_types'
# pw_fit_dict[cell_type] = (slope_mat, intercept_mat, discont_mat, pv_mat)

# slope_mat, intercept_mat: G' x L, entries are slopes/intercepts
# discont_mat: G' x L-1, entries are discontinuity at layer boundaries
# pv_mat: G' x L, entries are p-values from LLR test (slope=0 vs slope != 0)
def pw_linear_fit(counts_mat, belayer_labels, belayer_depth, cell_type_df, ct_list, 
                  umi_threshold=None, idx_kept=None, pseudocount=1, t=0.1):
    
    if idx_kept is None:
        idx_kept=np.where(np.sum(counts_mat,1) > umi_threshold)[0]
    pseudo_counts_mat=counts_mat+pseudocount
    exposures=np.sum(pseudo_counts_mat,axis=0)
    cmat=pseudo_counts_mat[idx_kept,:]
    
    G,N=cmat.shape
    
    L=len(np.unique(belayer_labels))
    
    pw_fit_dict={}
    
    # ONE: compute for all cell types
    print('Poisson regression for ALL cell types')
    s0_mat,i0_mat,s1_mat,i1_mat,pv_mat=segmented_poisson_regression(cmat,
                                                   exposures, 
                                                   belayer_labels, 
                                                   belayer_depth,
                                                   L)
    
    slope_mat=np.zeros((len(idx_kept), L))
    intercept_mat=np.zeros((len(idx_kept), L))

    t=0.10
    inds1= (pv_mat < t)
    inds0= (pv_mat >= t)

    slope_mat[inds1] = s1_mat[inds1]
    intercept_mat[inds1] = i1_mat[inds1]

    slope_mat[inds0] = s0_mat[inds0]
    intercept_mat[inds0] = i0_mat[inds0]

    discont_mat=get_discont_mat(slope_mat, intercept_mat, belayer_labels, belayer_depth, L)
          
    pw_fit_dict['all_cell_types']=(slope_mat,intercept_mat,discont_mat, pv_mat)
    
    # TWO: compute for each cell type in ct_list
    cell_type_mat=cell_type_df.to_numpy()
    cell_type_names=np.array(cell_type_df.columns)
    for ct in ct_list:
        print(f'Poisson regression for cell type: {ct}')
        ct_ind=np.where(cell_type_names==ct)[0][0]
        
        ct_spots=np.where(cell_type_mat[:,ct_ind] > 0)[0]
        ct_spot_proportions=cell_type_mat[ct_spots,ct_ind]
        
        cmat_ct=cmat[:,ct_spots] * np.tile(ct_spot_proportions,(G,1))
        exposures_ct=exposures[ct_spots] * ct_spot_proportions
        belayer_labels_ct=belayer_labels[ct_spots]
        belayer_depth_ct=belayer_depth[ct_spots]

        s0_ct,i0_ct,s1_ct,i1_ct,pv_mat_ct=segmented_poisson_regression(cmat_ct,
                                                       exposures_ct, 
                                                       belayer_labels_ct, 
                                                       belayer_depth_ct,
                                                       L)

        slope_mat_ct=np.zeros((len(idx_kept), L))
        intercept_mat_ct=np.zeros((len(idx_kept), L))

        t=0.10
        inds1_ct= (pv_mat_ct < t)
        inds0_ct= (pv_mat_ct >= t)

        slope_mat_ct[inds1_ct] = s1_ct[inds1_ct]
        intercept_mat_ct[inds1_ct] = i1_ct[inds1_ct]

        slope_mat_ct[inds0_ct] = s0_ct[inds0_ct]
        intercept_mat_ct[inds0_ct] = i0_ct[inds0_ct]
        
        discont_mat=get_discont_mat(slope_mat_ct, intercept_mat_ct, belayer_labels_ct, belayer_depth_ct, L)

        pw_fit_dict[ct]=(slope_mat_ct, intercept_mat_ct, discont_mat, pv_mat_ct)
          
    return pw_fit_dict